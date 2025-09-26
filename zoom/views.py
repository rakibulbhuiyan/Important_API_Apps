from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from datetime import timedelta

from .models import ZoomMeeting
from .serializers import ZoomMeetingSerializer, CreateMeetingSerializer
from .zoom_utils import create_zoom_meeting, get_zoom_access_token




import logging
logger = logging.getLogger(__name__)

User = get_user_model()

class ZoomMeetingListCreateView(generics.ListCreateAPIView):
    serializer_class = ZoomMeetingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return ZoomMeeting.objects.filter(
            Q(host=user) | Q(participant=user)
        ).select_related('host', 'participant')
    
    def create(self, request):
        serializer = CreateMeetingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False, 
                'errors': serializer.errors
            }, status=400)
        
        try:
            data = serializer.validated_data
            
            # Set default time if not provided
            if not data.get('scheduled_time'):
                data['scheduled_time'] = timezone.now() + timedelta(minutes=30)
            
            # Create Zoom meeting
            zoom_meeting = create_zoom_meeting(
                topic=data['topic'],
                duration=data['duration'],
                start_time=data['scheduled_time']
            )
            
            # Find participant user if email provided
            participant_user = None
            if data.get('participant_email'):
                try:
                    participant_user = User.objects.get(email=data['participant_email'])
                except User.DoesNotExist:
                    pass
            
            # Save to database
            meeting = ZoomMeeting.objects.create(
                zoom_meeting_id=str(zoom_meeting['id']),
                host=request.user,
                participant=participant_user,
                participant_email=data.get('participant_email'),
                topic=zoom_meeting['topic'],
                agenda=data.get('agenda', ''),
                scheduled_time=data['scheduled_time'],
                duration=zoom_meeting['duration'],
                join_url=zoom_meeting['join_url'],
                start_url=zoom_meeting['start_url'],
                password=zoom_meeting.get('password', ''),
            )
            
            # Send email if participant email provided
            if data.get('participant_email'):
                self.send_invitation_email(meeting, data['participant_email'])
            
            return Response({
                'success': True,
                'message': 'Meeting created successfully',
                'data': ZoomMeetingSerializer(meeting).data
            }, status=201)
            
        except Exception as e:
            logger.error(f"Meeting creation error: {e}")
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=400)
    
    def send_invitation_email(self, meeting, email):
        try:
            subject = f"Zoom Meeting: {meeting.topic}"
            message = f"""
You're invited to join a Zoom meeting:

Topic: {meeting.topic}
Time: {meeting.scheduled_time.strftime('%B %d, %Y at %I:%M %p')}
Duration: {meeting.duration} minutes

Join URL: {meeting.join_url}
Meeting ID: {meeting.zoom_meeting_id}
Password: {meeting.password}

Host: {meeting.host.get_full_name() or meeting.host.username}
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=True
            )
        except Exception as e:
            logger.error(f"Email send error: {e}")

class ZoomMeetingDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ZoomMeetingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ZoomMeeting.objects.filter(
            Q(host=self.request.user) | Q(participant=self.request.user)
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_instant_meeting(request):
    """Create instant meeting"""
    try:
        participant_email = request.data.get('participant_email')
        topic = request.data.get('topic', 'Instant Meeting')
        
        # Create Zoom meeting
        zoom_meeting = create_zoom_meeting(
            topic=topic,
            duration=60,
            start_time=timezone.now()
        )
        
        # Find participant
        participant_user = None
        if participant_email:
            try:
                participant_user = User.objects.get(email=participant_email)
            except User.DoesNotExist:
                pass
        
        # Save to database
        meeting = ZoomMeeting.objects.create(
            zoom_meeting_id=str(zoom_meeting['id']),
            host=request.user,
            participant=participant_user,
            participant_email=participant_email,
            topic=topic,
            scheduled_time=timezone.now(),
            duration=60,
            join_url=zoom_meeting['join_url'],
            start_url=zoom_meeting['start_url'],
            password=zoom_meeting.get('password', ''),
            status='started'
        )
        
        return Response({
            'success': True,
            'message': 'Instant meeting created',
            'data': {
                'meeting_id': meeting.id,
                'zoom_meeting_id': meeting.zoom_meeting_id,
                'start_url': meeting.start_url,
                'join_url': meeting.join_url,
                'password': meeting.password,
                'topic': meeting.topic
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=400)
    

import uuid
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def join_meeting(request, meeting_id):
    """Get join URL for meeting (supports both UUID and Zoom meeting ID)"""
    try:
        meeting = None
        
        # Try to parse as UUID (your DB id)
        try:
            uuid_obj = uuid.UUID(str(meeting_id))
            meeting = ZoomMeeting.objects.filter(
                id=uuid_obj
            ).filter(
                Q(participant=request.user) | Q(host=request.user)
            ).first()
        except ValueError:
            # Not a UUID → treat as Zoom meeting ID
            meeting = ZoomMeeting.objects.filter(
                zoom_meeting_id=str(meeting_id)
            ).filter(
                Q(participant=request.user) | Q(host=request.user)
            ).first()

        if not meeting:
            return Response({
                'success': False,
                'message': 'Meeting not found or access denied'
            }, status=404)

        return Response({
            'success': True,
            'data': {
                'join_url': meeting.join_url,
                'meeting_id': meeting.zoom_meeting_id,
                'password': meeting.password,
                'topic': meeting.topic
            }
        })

    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=400)
    


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def start_meeting(request, meeting_id):
    """Get start URL for meeting host (supports both UUID and Zoom meeting ID)"""
    try:
        meeting = None

        # Try UUID lookup
        try:
            uuid_obj = uuid.UUID(str(meeting_id))
            meeting = ZoomMeeting.objects.filter(
                id=uuid_obj,
                host=request.user
            ).first()
        except ValueError:
            # Fallback to Zoom meeting ID
            meeting = ZoomMeeting.objects.filter(
                zoom_meeting_id=str(meeting_id),
                host=request.user
            ).first()

        if not meeting:
            return Response({
                'success': False,
                'message': 'Meeting not found or access denied'
            }, status=404)

        # Update status
        meeting.status = 'started'
        meeting.save()

        return Response({
            'success': True,
            'data': {
                'start_url': meeting.start_url,
                'meeting_id': meeting.zoom_meeting_id,
                'password': meeting.password,
                'topic': meeting.topic
            }
        })

    except Exception as e:
        return Response({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=400)

# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods
# import json

# @csrf_exempt
# @require_http_methods(["POST"])
# def zoom_webhook(request):
#     """Handle Zoom webhook events"""
#     try:
#         payload = json.loads(request.body.decode('utf-8'))
#         event_type = payload.get('event')
#         meeting_data = payload.get('payload', {}).get('object', {})
#         meeting_id = str(meeting_data.get('id', ''))

#         logger.info(f"Received Zoom webhook: {event_type} for meeting {meeting_id}")

#         if not meeting_id:
#             return JsonResponse({'status': 'ignored'}, status=200)

#         try:
#             meeting = ZoomMeeting.objects.get(zoom_meeting_id=meeting_id)
#         except ZoomMeeting.DoesNotExist:
#             return JsonResponse({'status': 'meeting_not_found'}, status=200)

#         # Handle events
#         if event_type == 'meeting.started':
#             meeting.mark_as_started()
#             MeetingLog.objects.create(
#                 meeting=meeting,
#                 log_type='started',
#                 message='Meeting started',
#                 metadata=meeting_data
#             )

#         elif event_type == 'meeting.ended':
#             meeting.mark_as_ended()
#             MeetingLog.objects.create(
#                 meeting=meeting,
#                 log_type='ended',
#                 message='Meeting ended',
#                 metadata=meeting_data
#             )

#         elif event_type == 'meeting.participant_joined':
#             participant_data = meeting_data.get('participant', {})
#             email = participant_data.get('email')
#             MeetingLog.objects.create(
#                 meeting=meeting,
#                 log_type='participant_joined',
#                 message=f"Participant {email} joined",
#                 metadata=participant_data
#             )

#         elif event_type == 'meeting.participant_left':
#             participant_data = meeting_data.get('participant', {})
#             email = participant_data.get('email')
#             MeetingLog.objects.create(
#                 meeting=meeting,
#                 log_type='participant_left',
#                 message=f"Participant {email} left",
#                 metadata=participant_data
#             )

#         return JsonResponse({'status': 'processed'}, status=200)

#     except Exception as e:
#         logger.error(f"Webhook processing error: {e}")
#         return JsonResponse({'status': 'error'}, status=400)






@api_view(['GET'])
def test_zoom_connection(request):
    """Test Zoom API connection with detailed info"""
    try:
        from .zoom_utils import test_zoom_connection as test_connection
        
        result = test_connection()
        if result["success"]:
            return Response({
                'success': True,
                'message': 'Zoom connection successful!',
                'data': {
                    'user_id': result.get('user_id'),
                    'email': result.get('email'),
                    'account_id': result.get('account_id'),
                    'api_ready': True
                }
            })
        else:
            return Response({
                'success': False,
                'message': result["message"],
                'api_ready': False
            }, status=400)
            
    except Exception as e:
        logger.error(f"Test connection error: {e}")
        return Response({
            'success': False,
            'message': f'Connection test failed: {str(e)}',
            'api_ready': False
        }, status=400)