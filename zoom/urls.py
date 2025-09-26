from django.urls import path
from . import views

app_name = 'apps.zoom'

urlpatterns = [
    # Meeting management
    path('meetings/', views.ZoomMeetingListCreateView.as_view(), name='meeting-list-create'),
    path('meetings/<uuid:pk>/', views.ZoomMeetingDetailView.as_view(), name='meeting-detail'),
    
    # Quick actions
    path('instant-meeting/', views.create_instant_meeting, name='instant-meeting'),
    path('join/<uuid:meeting_id>/', views.join_meeting, name='join-meeting'), # as participant
    path('start/<uuid:meeting_id>/', views.start_meeting, name='start-meeting'), # as host
    



    # path('webhook/', views.zoom_webhook, name='zoom-webhook'),
    # Test
    path('test/', views.test_zoom_connection, name='test-connection'),
]