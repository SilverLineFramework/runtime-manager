"""Orchestrator APIs."""

from django.urls import path

from . import views


urlpatterns = [
    path('runtimes/', views.list_runtimes),
    path('runtimes/<str:query>/', views.search_runtime),
    path('modules/', views.list_modules),
    path('modules/<str:query>/', views.search_module),
    path('queued/', views.queued_modules)
]
