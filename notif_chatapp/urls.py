from django.urls import path
from .views import *

urlpatterns = [

    path("notifications/", NotificationListAPI.as_view(), name="notification-list"),
    path("notif/<int:pk>/read/", NotificationMarkReadAPI.as_view(), name="notification-mark-read"),
    path("mark-read/", NotificationBulkMarkReadAPI.as_view(), name="notification-bulk-mark-read"),
    path("mark-all-read/", NotificationMarkAllReadAPI.as_view(), name="notification-mark-all-read"),
    path("unread-count/", NotificationUnreadCountAPI.as_view(), name="notification-unread-count"),
    path("preferences/", NotificationPreferenceAPI.as_view(), name="notification-preferences"),
    path("test-notification/", TestNotificationAPI.as_view(), name="test-notification"),
]
