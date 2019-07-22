from typing import List

from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import viewsets, generics

from dataclasses import dataclass
from enum import Enum

import os

import re
import requests

from .models import Dependency


class VersionType(Enum):
    EXACT = 1
    GTE = 2
    LTE = 3


@dataclass
class Dependency:
    name: str
    version: str
    version_type: VersionType

    @classmethod
    def from_str(cls, vers: str) -> Dependency:
        pass


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


def deps_from_installed(name: str, version: str) -> List[Dependency]:
    """Check for dist-info and egg-info, and delegate to the appropriate
    sub function to find dependency info."""

    result = []

    with open(f"deps_to_query/{name}-{version}.dist-info/METADATA") as f:
        for line in f.readlines():
            m = re.match(r"^Requires-Dist:\s+(.*)\s+\((.*)\)$", line)


    # is requires.txt/egg-info legacy?
    with open(f"deps_to_query/{name}-{version}.egg-info/requires.txt") as f:
        for line in f.readlines():
            result.append(Dependency.from_str(line))

   return result


def cleanup_dep(name: str, version: str) -> None:
    # todo: Should we specify version, or just name?

    os.env["PYTHONPATH"] = "deps_to_query"
    # name_with_version = f"{name}=={version}"
    os.system(f"python -m pip uninstall {name}")


def install_with_pip(name: str, version: str) -> None:
    # Version is exact.
    name_with_version = f"{name}=={version}"
    os.system(f"python -m pip install {name_with_version} --target deps_to_query")


def download_package(name: str, version: str) -> None:
    url = f"https://pypi.org/pypi/{name}/json"
    data = requests.get(url).json()


def update_all() -> None:
    """Update all packagse"""
    pass


# Create your views here.
@api_view(["GET"])
def get_schedule_data(request: Request):
    """"""
    return Response({})


# class BookList(generics.ListCreateAPIView):
#     queryset = Work.objects.all()
#     serializer_class = WorkSerializer
#     permission_classes = (permissions.IsAdminUser,)
