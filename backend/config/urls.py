from django.urls import path

from routing import views

urlpatterns = [
    path("api/plan", views.plan),
    path("api/geocode", views.geocode),
]
