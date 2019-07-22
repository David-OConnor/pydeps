from typing import List

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


class VersionType(Enum):
    EXACT = 1
    GTE = 2
    LTE = 3
    NE = 4


# @dataclass
# class Requirement:
#     name: str
#     version: str
#     version_type: VersionType
#
#     @classmethod
#     def from_str(cls, vers: str) -> Dependency:
#         pass


# def deps_from_requires(path: str) -> List[Dependency]:
#     """ie packagename.egg-info/requires.txt.  Legacy?"""
#     with open(path + "/requires.txt") as f:
#         for line in f.readlines:
#             print("LINE: ", line)
#
#
# def deps_from_metadata(path: str) -> List[Dependency]:
#     """ie packagename.dist-info/METADATA"""
#     with open(path + "/METADATA") as f:
#         for line in f.readlines:
#             print("LINE: ", line)


def deps_from_installed(dep: Dependency) -> List[Requirement]:
    """Check for dist-info and egg-info, and delegate to the appropriate
    sub function to find dependency info."""

    result = []

    with open(f"{str(Path.cwd())}/deps_to_query/{dep.name}-{dep.version}.dist-info/METADATA") as f:
        for line in f.readlines():
            m = re.match(r"^Requires-Dist:\s+(.*)\s+\((.*)\)$", line)
            if m:
                req_name, req_v = m.groups()
                result.append(Requirement(name=req_name, versions=req_v, dependency=dep))

    # # is requires.txt/egg-info legacy?
    # with open(f"deps_to_query/{name}-{version}.egg-info/requires.txt") as f:
    #     for line in f.readlines():
    #         result.append(Requirement.from_str(line))

    return result


# def cleanup_dep(name: str, version: str) -> None:
#     # todo: Should we specify version, or just name?
#     # Having trouble uninstalling from outside environment; just delete
#
#
#
#     d = dict(os.environ)  # Make a copy of the current environment
#     d["PYTHONPATH"] = "deps_to_query"
#     subprocess.Popen(['python', '-m', 'pip', 'uninstall', name], env=d)
#
#
#     # # os.environ["PYTHONPATH"] = "deps_to_query"
#     # # name_with_version = f"{name}=={version}"
#     # os.system(f"python -m pip uninstall {name}")

def cleanup_downloaded() -> None:
    """Remove all download dependencies; they're temporary"""
    for path in Path("deps_to_query").glob("**/*"):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            rmtree(path)


def install_with_pip(name: str, version: str) -> None:
    # Version is exact.
    name_with_version = f"{name}=={version}"
    os.system(f"python -m pip install {name_with_version} --target deps_to_query")


# def download_package(name: str, version: str) -> None:
#     url = f"https://pypi.org/pypi/{name}/json"
#     data = requests.get(url).json()


def cache_dep(name: str, version: str)  -> None:
    """Wrapper for subfns: Downloads a dep, pulls subdeps, cleans up
    downloaded files"""
    install_with_pip(name, version)
    for dep in deps_from_installed(name, version):
        dep_db = Requirement(
            name=dep.name,
            version=dep.version,

        )

        dep_db.save()

    cleanup_downloaded()


# def update_all() -> None:
#     """Update all packagse"""
#     pass


# Create your views here.
@api_view(["GET"])
def get_schedule_data(request: Request):
    """"""
    print("REQUEST: ", request)

    try:
        reqs = Requirement.objects.filter(dependency__name=request.name, dependency__version=request.version)
        req_serializer = ReqSerializer(reqs, many=True)
        return Response({"requirements": req_serializer.data})

    except Requirement.DoesNotExist:
        print("DOESN't Exist")
        cache_dep(request.name, request.version)
