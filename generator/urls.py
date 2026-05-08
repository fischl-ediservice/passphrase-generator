from django.urls import path
from . import views

app_name = "generator"

urlpatterns = [
    path("",                                   views.index,          name="index"),
    path("generate/",                          views.generate,       name="generate"),
    path("profile/save/",                      views.save_profile,   name="save_profile"),
    path("profile/<uuid:profile_id>/delete/",  views.delete_profile, name="delete_profile"),
]
