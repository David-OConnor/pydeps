from django.db import models


class Dependency(models.Model):
    name = models
    version = models.CharField(max_length=30)  # Includes version info
