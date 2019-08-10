from django.contrib import admin

from .models import Dependency, Requirement


class DepAdmin(admin.ModelAdmin):
    # ordering = ['date_created']
    search_fields = ["name", "version"]


class ReqAdmin(admin.ModelAdmin):
    # ordering = ['date_created']
    search_fields = ["data", "dependency__name"]


# Register your models here.
admin.site.register(Dependency, DepAdmin)
admin.site.register(Requirement, ReqAdmin)
