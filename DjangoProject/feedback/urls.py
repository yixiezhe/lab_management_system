from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FeedbackViewSet

router = DefaultRouter()
router.register(r"items", FeedbackViewSet, basename="feedback")

urlpatterns = [
    path("", include(router.urls)),
]
