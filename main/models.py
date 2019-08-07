from typing import List

from django.db import models


class Dependency(models.Model):
    """An analog of DepNode in pypackage."""

    # todo: Perhaps store filename, hash etc here, so we don't pull multiple times in pypackage.
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=100)  # Includes version info
    requires_python = models.CharField(max_length=200, blank=True, null=True)
    reqs_complete = models.BooleanField(default=False)

    # filename = models.CharField(max_length=100)
    # hash = models.CharField(max_length=300)
    # file_url = models.CharField(max_length=500)
    # version_reqs = models.ManyToManyField(Requirement)
    # dependencies = models.ManyToManyField("self")

    def requires_dist(self) -> List[str]:
        """ We only use Requirement as a separate model, since there's no
        no good way to represent a list in a relational DB. For serialization,
        we just want the text"""
        return [req.data for req in Requirement.objects.filter(dependency=self)]

    def __repr__(self):
        return f'{self.name}: "{self.version}"'

    def __str__(self):
        return self.__repr__()

    class Meta:
        unique_together = ("name", "version")


class Requirement(models.Model):
    # Let's not handle parsing in this project.
    data = models.CharField(max_length=500)

    # name = models.CharField(max_length=100)
    # eg "!=2.0.4,!=2.1.2,!=2.1.6,>=2.0.1"
    # versions = models.CharField(max_length=500)
    dependency = models.ForeignKey(
        Dependency, related_name="requirements", on_delete=models.CASCADE
    )

    # def from_str(self, dependency: Dependency) -> Requirement:
    #     return Requirement(name=name, versions=versions)

    def __repr__(self):
        return f'{self.data}, required by {self.dependency.name}="{self.dependency.version}"'

    def __str__(self):
        return self.__repr__()


    class Meta:
        unique_together = ("data", "dependency")
