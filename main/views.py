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


class DepSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dependency
        # name isn't required, since we return these as a list of versions
        # for the same name.
        fields = ("version", "requires_python", "requires_dist")
        depth = 1


class ReqSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requirement
        fields = ("name", "versions")


def reqs_from_installed(dep: Dependency) -> Optional[List[Requirement]]:
    """Check for dist-info and egg-info, and delegate to the appropriate
    sub function to find dependency info."""
    result = []

    try:
        with open(
            f"{str(Path.cwd())}/deps_to_query/{dep.name}-{dep.version}.dist-info/METADATA"
        ) as f:
            for line in f.readlines():
                # Ignore bits after semicolon. (?)
                m = re.match(r"^Requires-Dist:\s*(.*)$", line)
                if m:
                    data = m.groups()[0]

                    result.append(
                        Requirement(data=data, dependency=dep)
                    )
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
    # cleanup_downloaded()


@api_view(["GET"])
def get_data(request: Request, name: str, version: str):
    """Get dependency data for a single version"""
    try:
        Dependency.objects.get(name=name, version=version)
    except Dependency.DoesNotExist:
        cache_dep(name, version)

    reqs = Requirement.objects.filter(
        dependency__name=name, dependency__version=version
    )
    req_serializer = ReqSerializer(reqs, many=True)
    return Response({"requirements": req_serializer.data})


@api_view(["GET"])
def get_all(request: Request, name: str):
    """Get dependency data for all versions of a package. Allows us to pull
    requirements for all versions of a package with one API hit - Pypi requires
    a hit for each version. We collect and cache that. This may take a while when getting
    for packages with a large number of uncached versions."""

    # Get all versions from the warehouse
    r = requests.get(f"https://pypi.org/pypi/{name}/json").json()
    versions = r["releases"].keys()

    result = []
    for version in versions:
        try:
            dep = Dependency.objects.get(name=name, version=version)
            if not dep.reqs_complete:
                # Possible interruption between saving the dep, and adding the reqs.
                print(f"Reqs not complete for {name}, {version}. Downloading and checking manually.")
                cache_dep(name, version)
            result.append(dep)
        except Dependency.DoesNotExist:
            data = requests.get(f"https://pypi.org/pypi/{name}/{version}/json").json()
            info = data["info"]
            dep = Dependency(
                name=name,
                version=version,
                requires_python=info["requires_python"],
            )

            try:
                dep.save()
            except IntegrityError:
                # Possibly a conflict between multiple requests. If this happens,
                # make sure we pull req info again. (?)
                print("Integrity error; trying to get dep again.")
                dep = Dependency.objects.get(name=name, version=version)

            if info["requires_dist"] is None:
                # This may mean there are no dependencies, or Pypi is unable to properly
                # find them. Unfortunately, there's currently no way to tell the difference.
                # todo: Even if not none, we may not be able to trust Pypi.
                # todo: Perhaps always determine ourselves?
                print(f"Deps is empty on pypi warehouse for {name}, {version}. Downloading and checking manually.")
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
            print(f"Cached {name} = \"{version}\" ")
            result.append(dep)

    dep_serializer = DepSerializer(result, many=True)
    return Response(dep_serializer.data)
