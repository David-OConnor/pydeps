"""pydeps URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path


from django.urls import include, path
from rest_framework import routers

# from tutorial.quickstart import views


from main import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("multiple/", views.multiple),
    path("<str:name>/<str:version>/", views.get_one),
    path("<str:name>/", views.get_all),
    path("gte/<str:name>/<str:version>/", views.get_gte),
    path("lte/<str:name>/<str:version>/", views.get_lte),
    path("range/<str:name>/<str:min_vers>/<str:max_vers>/", views.get_range),
]
