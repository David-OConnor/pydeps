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
import zipfile

# from dataclasses import dataclass
# from enum import Enum

import os  # , subprocess

import re

from .models import Dependency, Requirement

# We keep versions as strings in this package for consistency with the database, file reads,
# and rest endpoints.

import sys  # todo todo temp


def print_heroku(s: str):
    print(s)
    sys.stdout.flush()


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
        # todo: Not as robust as the Rust version for handling modifiers etc.
        maj_only = re.match(r"^(\d{1,9})\.?(.*)$", s)
        maj_minor = re.match(r"^(\d{1,9})\.(\d{1,9})\.?(.*)$", s)
        maj_minor_patch = re.match(r"^(\d{1,9})\.(\d{1,9})\.(\d{1,9})\.?(.*)$", s)

        if maj_minor_patch:
            major, minor, patch, modifier = maj_minor_patch.groups()
            return cls(int(major), int(minor), int(patch), modifier)
        if maj_minor:
            major, minor, modifier = maj_minor.groups()
            return cls(int(major), int(minor), 0, modifier)
        if maj_only:
            major, modifier = maj_only.groups()
            return cls(int(major), 0, 0, modifier)

        # raise ValueError(f"Unable to parse Version from {s}")
        return None

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}{self.modifier}"


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
    names_to_try = [
        dep.name.replace("-", "_").capitalize(),
        dep.name.replace("-", "_").lower(),
        dep.name.replace("_", "-").capitalize(),
        dep.name.replace("_", "-").lower(),
    ]
    for name in names_to_try:
        try:
            with open(
                f"{str(Path.cwd())}/deps_to_query/{name}-{dep.version}.dist-info/METADATA"
            ) as f:
                for line in f.readlines():
                    m = re.match(r"^Requires-Dist:\s*(.*)$", line)
                    if m:
                        data = m.groups()[0]

                        result.append(Requirement(data=data, dependency=dep))
        except FileNotFoundError:
            continue

    return result


def cleanup_downloaded() -> None:
    """Remove all download dependencies; they're temporary"""
    for path in Path("deps_to_query").glob("**/*"):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            rmtree(path)


def install_from_wheel(dep: Dependency) -> None:
    """Try this first; if unable to find a wheel, use install_with_pip.
    Doing this avoids installing sub-dependencies, and issues where we
    can't install due to Heroku using an old version of pip incompatible
    with manylinux2010, and problems building from source."""

    # Version is exact.
    data = requests.get(f"https://pypi.org/pypi/{dep.name}/json").json()
    releases = data["releases"]
    found_wheel = False

    for rel_v, rel_data in releases.items():
        if rel_v == dep.version:
            # Pick the first wheel you find.
            for rel in rel_data:
                if rel["packagetype"] == "bdist_wheel":
                    found_wheel = True
                    downloaded_wheel = requests.get(rel["url"])
                    archive_path = f"deps_to_query/{rel['filename']}"
                    with open(archive_path, "wb") as f:
                        f.write(downloaded_wheel.content)
                        try:
                            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                                zip_ref.extractall("deps_to_query")
                        except zipfile.BadZipFile:
                            print("Bad zipfile on ", dep)
                            continue

                        zip_ref.close()
                    sys.stdout.flush()  # so we can output errors on heroku
                    break
            break
    if not found_wheel:
        print_heroku(f"Can't find a wheel; installing {dep} with Pip")
        install_with_pip(dep)


def install_with_pip(dep: Dependency) -> None:
    # Version is exact.
    name_with_version = f"{dep.name}=={dep.version}"
    os.system(f"python3 -m pip install {name_with_version} --target deps_to_query")
    sys.stdout.flush()


def cache_dep(name: str, version: str) -> None:
    """Wrapper for subfns: Downloads a dep, pulls subdeps, cleans up
    downloaded files. Stores deps and reqs to database"""
    name = name.replace("_", "-").lower()
    dep, created = Dependency.objects.get_or_create(name=name, version=version)

    install_from_wheel(dep)

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
    name = name.replace("_", "-").lower()

    for version in versions:
        # version = str(version) # todo put back once version handles modifiers
        try:
            # valid_names = [name.replace("-", "_"), name.replace("_", "-").lower()]
            # todo: May need a case check too, but can't chain _in and __iexact,
            # todo, and it appears that all db entries are lowercase
            dep = Dependency.objects.get(name=name, version=version)
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
                dep = Dependency.objects.get(
                    name=name.replace("_", "-").lower(), version=version
                )

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
            print_heroku(f'Cached {name} = "{version}" ')
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
    """This is the main API used by Pyflow; it can load arbitrary package/version combos
    in one request, but requires passing the versions to query in the request."""
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
