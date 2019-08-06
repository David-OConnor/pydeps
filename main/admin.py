from django.contrib import admin

from .models import Dependency, Requirement

# Register your models here.
admin.site.register(Dependency)
admin.site.register(Requirement)