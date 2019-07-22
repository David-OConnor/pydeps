from typing import List, Optional

from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import viewsets, generics, serializers

from pathlib import Path
from shutil import rmtree

from dataclasses import dataclass
from enum import Enum

import os, subprocess

import re

# import requests

from .models import Dependency, Requirement


class DepSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dependency
        fields = ("name", "version", "requirements")


class ReqSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requirement
        fields = ("name", "versions")


# class VersionType(Enum):
#     EXACT = 1
#     GTE = 2
#     LTE = 3
#     NE = 4


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
                m = re.match(r"^Requires-Dist:\s+(.*?)(?:\s+\((.*?)\))?(?:;.*)?$", line)
                if m:
                    req_name, req_v = m.groups()

                    if req_v is None:  # ie not specified / any version allowed
                        req_v = ""
                    result.append(
                        Requirement(name=req_name, versions=req_v, dependency=dep)
                    )
    except FileNotFoundError:
        return None  # This *may* mean the dependency cannot be found / doesn't exist.

    # # is requires.txt/egg-info legacy?
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
    os.system(f"python -m pip install {name_with_version} --target deps_to_query")


def cache_dep(name: str, version: str) -> None:
    """Wrapper for subfns: Downloads a dep, pulls subdeps, cleans up
    downloaded files. Stores deps and reqs to database"""
    dep, created = Dependency.objects.get_or_create(name=name, version=version)

    install_with_pip(dep)

    reqs = reqs_from_installed(dep)
    if reqs is not None:
        for req in reqs:
            req.save()

        # Don't save the dep unless also saving its associated reqs.
        if created:
            dep.save()

    # cleanup_downloaded()


# Create your views here.
@api_view(["GET"])
def get_data(request: Request, name: str, version: str):
    """"""
    try:
        dep = Dependency.objects.get(name=name, version=version)
    except Dependency.DoesNotExist:
        print("CAN't FIND IT", name)
    cache_dep(name, version)

    reqs = Requirement.objects.filter(
        dependency__name=name, dependency__version=version
    )
    req_serializer = ReqSerializer(reqs, many=True)
    return Response({"requirements": req_serializer.data})
