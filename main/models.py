from django.db import models


class Dependency(models.Model):
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=30)  # Includes version info

    def __repr__(self):
        return f"{self.name}: {self.version}"


class Requirement(models.Model):
    name = models.CharField(max_length=100)
    # eg "!=2.0.4,!=2.1.2,!=2.1.6,>=2.0.1"
    versions = models.CharField(max_length=500)
    dependency = models.ForeignKey(Dependency, related_name="requirements", on_delete=models.CASCADE)

    def __repr__(self):
        return f"{self.name}: {self.versions}, Dep: {self.dependency.name}: {self.dependency.version}"
