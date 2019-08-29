from dataclasses import dataclass
from functools import total_ordering
from typing import List, Optional

import requests
from django.db import IntegrityError

from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import serializers

from pathlib import Path
from shutil import rmtree

# from dataclasses import dataclass
# from enum import Enum

import os  # , subprocess

import re

from .models import Dependency, Requirement

# We keep versions as strings in this package for consistency with the database, file reads,
# and rest endpoints.


@dataclass
@total_ordering
class Version:
    major: int
    minor: int
    patch: int
    # todo: Need to parse/format modifier if you want to use this .
    modifier: str  # includes extra nums, and modifiers.

    def __eq__(self: "Version", other: "Version") -> bool:
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
        )

    def __gt__(self: "Version", other: "Version") -> bool:
        if self.major != other.major:
            return self.major > other.major
        if self.minor != other.minor:
            return self.minor > other.minor
        if self.patch != other.patch:
            return self.patch > other.patch
        return False

    @classmethod
    def from_str(cls: "Version", s: str) -> Optional["Version"]:
        maj_only = re.match(r"^(\d{1,9})\.?$", s)
        maj_minor = re.match(r"^(\d{1,9})\.(\d{1,9})\.?$", s)
        maj_minor_patch = re.match(r"^(\d{1,9})\.(\d{1,9})\.(\d{1,9})\.?$", s)

        if maj_minor_patch:
            major, minor, patch = maj_minor_patch.groups()
            return cls(int(major), int(minor), int(patch), "")
        if maj_minor:
            major, minor = maj_minor.groups()
            return cls(int(major), int(minor), 0, "")
        if maj_only:
            major = maj_only.group()
            return cls(int(major), 0, 0, "")

        # raise ValueError(f"Unable to parse Version from {s}")
        return None

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


class DepSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dependency
        # name isn't required, since we return these as a list of versions
        # for the same name.
        fields = ("version", "requires_python", "requires_dist")
        depth = 1

class DepSerializerWName(serializers.ModelSerializer):
    class Meta:
        model = Dependency
        # name isn't required, since we return these as a list of versions
        # for the same name.
        fields = ("name", "version", "requires_python", "requires_dist")
        depth = 1


class ReqSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requirement
        fields = ("data",)


def reqs_from_installed(dep: Dependency) -> Optional[List[Requirement]]:
    """Check for dist-info and egg-info, and delegate to the appropriate
    sub function to find dependency info."""
    result = []
    try:
        with open(
            f"{str(Path.cwd())}/deps_to_query/{dep.name}-{dep.version}.dist-info/METADATA"
        ) as f:
            for line in f.readlines():
                m = re.match(r"^Requires-Dist:\s*(.*)$", line)
                if m:
                    data = m.groups()[0]

                    result.append(Requirement(data=data, dependency=dep))


    except FileNotFoundError:
        # todo DRY!
        # Try again, but capitalized
        try:
            with open(
                    f"{str(Path.cwd())}/deps_to_query/{dep.name.capitalize()}-{dep.version}.dist-info/METADATA"
            ) as f:
                for line in f.readlines():
                    m = re.match(r"^Requires-Dist:\s*(.*)$", line)
                    if m:
                        data = m.groups()[0]

                        result.append(Requirement(data=data, dependency=dep))
        except FileNotFoundError:
            print(f"Can't find dist-info for {dep.name}-{dep.version}")
            return []  # This *may* mean the dependency cannot be found / doesn't exist.

    # with open(f"deps_to_query/{name}-{version}.egg-info/requires.txt") as f:
    #     for line in f.readlines():
    #         result.append(Requirement.from_str(line))

    return result


def cleanup_downloaded() -> None:
    """Remove all download dependencies; they're temporary"""
    for path in Path("deps_to_query").glob("**/*"):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            rmtree(path)


def install_with_pip(dep: Dependency) -> None:
    # Version is exact.
    name_with_version = f"{dep.name}=={dep.version}"
    os.system(f"python3 -m pip install {name_with_version} --target deps_to_query")


def cache_dep(name: str, version: str) -> None:
    """Wrapper for subfns: Downloads a dep, pulls subdeps, cleans up
    downloaded files. Stores deps and reqs to database"""
    name = name.replace("_", "-").lower()
    dep, created = Dependency.objects.get_or_create(name=name, version=version)

    install_with_pip(dep)

    reqs = reqs_from_installed(dep)
    # if reqs is not None:
    for req in reqs:
        try:
            req.save()
        except IntegrityError:
            continue

    # Don't save the dep unless also saving its associated reqs.
    if created:
        dep.save()

    if not dep.reqs_complete:
        dep.reqs_complete = True
        dep.save()
    cleanup_downloaded()


# todo: Until version handles modifiers
# def process_reqs(name: str, versions: List[Version]) -> List[Dependency]:
def process_reqs(name: str, versions: List[str]) -> List[Dependency]:
    """Helper function to reduce repetition"""
    result_ = []

    for version in versions:
        # version = str(version) # todo put back once version handles modifiers
        try:
            # valid_names = [name.replace("-", "_"), name.replace("_", "-").lower()]
            # todo: May need a case check too, but can't chain _in and __iexact,
            # todo, and it appears that all db entries are lowercase
            dep = Dependency.objects.get(name=name.replace("_", "-").lower(), version=version)
            if not dep.reqs_complete:
                # Possible interruption between saving the dep, and adding the reqs.
                print(
                    f"Reqs not complete for {name}, {version}. Downloading and checking manually."
                )
                cache_dep(name, version)
                result_.append(dep)
        except Dependency.DoesNotExist:

            data = requests.get(f"https://pypi.org/pypi/{name}/{version}/json").json()
            info = data["info"]
            dep = Dependency(
                name=name, version=version, requires_python=info["requires_python"]
            )

            try:
                dep.save()
            except IntegrityError:
                # Possibly a conflict between multiple requests. If this happens,
                # make sure we pull req info again. (?)
                print("Integrity error; trying to get dep again.")
                # There's inconsistent package name formatting across the ecosystem.
                # valid_names = [name.replace("-", "_"), name.replace("_", "-")]
                dep = Dependency.objects.get(name=name.replace("_", "-").lower(), version=version)

            if info["requires_dist"] is None:
                # This may mean there are no dependencies, or Pypi is unable to properly
                # find them. Unfortunately, there's currently no way to tell the difference.
                # todo: Even if not none, we may not be able to trust Pypi.
                # todo: Perhaps always determine ourselves?
                print(
                    f"Deps is empty on pypi warehouse for {name}, {version}. Downloading and checking manually."
                )
                cache_dep(name, version)
            else:
                for req in info["requires_dist"]:
                    req2 = Requirement(data=req, dependency=dep)
                    try:
                        req2.save()
                    except IntegrityError:
                        continue
            dep.reqs_complete = True
            dep.save()
            print(f'Cached {name} = "{version}" ')
            print("DEP", dep)
        if name == "prompt-toolkit":
            pass

        result_.append(dep)
    return result_


def get_helper(name: str, min_vers: Optional[Version], max_vers: Optional[Version]):
    r = requests.get(f"https://pypi.org/pypi/{name}/json").json()

    versions = [Version.from_str(v) for v in r["releases"].keys()]
    versions = [v for v in versions if v is not None]

    if min_vers:
        versions = [v for v in versions if v >= min_vers]
    if max_vers:
        versions = [v for v in versions if v <= max_vers]

    dep_serializer = DepSerializer(process_reqs(name, versions), many=True)
    return Response(dep_serializer.data)


@api_view(["GET"])
def get_one(request: Request, name: str, version: str):
    vers = Version.from_str(version)
    return get_helper(name, vers, vers)


@api_view(["GET"])
def get_all(request: Request, name: str):
    """Get dependency data for all versions of a package. Allows us to pull
    requirements for all versions of a package with one API hit - Pypi requires
    a hit for each version. We collect and cache that. This may take a while when getting
    for packages with a large number of uncached versions."""
    return get_helper(name, None, None)


@api_view(["GET"])
def get_gte(request: Request, name: str, version: str):
    """Similar to get_all, but only get reqs greater greater than a specific version.
    Has faster catching than get_all."""
    return get_helper(name, Version.from_str(version), None)


@api_view(["GET"])
def get_lte(request: Request, name: str, version: str):
    return get_helper(name, None, Version.from_str(version))


@api_view(["GET"])
def get_range(request: Request, name: str, min_vers: str, max_vers: str):
    return get_helper(name, Version.from_str(min_vers), Version.from_str(max_vers))


@api_view(["POST"])
def multiple(request: Request):
    result = []

    for name, versions in request.data["packages"].items():
        # todo: Perhaps put this logic back if you update Version to parse and format
        # todo modifiers (ie 1.2.3.4b3
        # versions = [Version.from_str(v) for v in versions]
        # result.extend(process_reqs(name, [v for v in versions if v is not None]))
        result.extend(process_reqs(name, versions))

    dep_serializer = DepSerializerWName(result, many=True)
    # print(dep_serializer.data, "\n\n")
    return Response(dep_serializer.data)
