from django.urls import path

from . import views

app_name = "moderation"

urlpatterns = [
    path("", views.queue, name="queue"),
    path("<uuid:pk>/", views.review, name="review"),
    path("<uuid:pk>/approve/", views.approve, name="approve"),
    path("<uuid:pk>/reject/", views.reject, name="reject"),
    path("<uuid:pk>/hide/", views.hide, name="hide"),
    path("<uuid:pk>/restore/", views.restore, name="restore"),
    path("<uuid:pk>/rescan/", views.rescan, name="rescan"),
]
