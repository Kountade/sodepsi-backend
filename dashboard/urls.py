# apps/dashboard/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DashboardViewSet, StatistiqueViewSet, AnalyseViewSet

router = DefaultRouter()

# Trois ViewSets distincts avec leurs propres endpoints
router.register('dashboard', DashboardViewSet, basename='dashboard')
router.register('statistique', StatistiqueViewSet, basename='statistique')
router.register('analyse', AnalyseViewSet, basename='analyse')

urlpatterns = [
    path('', include(router.urls)),
]
