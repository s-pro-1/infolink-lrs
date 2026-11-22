from django.urls import path

from . import views

app_name = "resources"

urlpatterns = [
    path("", views.browse, name="browse"),
    path("upload/", views.upload, name="upload"),
    path("mine/", views.my_uploads, name="mine"),
    path("<uuid:pk>/", views.detail, name="detail"),
    path("<uuid:pk>/download/", views.download, name="download"),
]
