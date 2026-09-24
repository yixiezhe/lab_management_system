from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import GroupAffairBoardViewSet, GroupAffairDutyReminderReadView, GroupAffairUnreadPopupView, GroupPurchasePopupReadView

router = DefaultRouter()
router.register(r"boards", GroupAffairBoardViewSet, basename="group-affair-board")

urlpatterns = [
    path("", include(router.urls)),
    path("popups/unread/", GroupAffairUnreadPopupView.as_view(), name="group-affair-unread-popups"),
    path(
        "popups/duty-reminder/mark-read/",
        GroupAffairDutyReminderReadView.as_view(),
        name="group-affair-duty-reminder-read",
    ),
    path("popups/purchase/mark-read/", GroupPurchasePopupReadView.as_view(), name="group-purchase-popup-read"),
]
