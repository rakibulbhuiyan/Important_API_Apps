# Updated zoom_utils.py with cache fix
import base64
import requests
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Your credentials
ZOOM_CLIENT_ID = "**********"
ZOOM_CLIENT_SECRET = "*******"
ZOOM_ACCOUNT_ID = "************"

def clear_zoom_token_cache():
    """Clear cached zoom token to force refresh"""
    cache.delete('zoom_token')
    print("🗑️ Zoom token cache cleared")

def get_zoom_access_token(force_refresh=False):
    """
    Get Zoom Server-to-Server OAuth token with option to force refresh.
    """
    if force_refresh:
        cache.delete('zoom_token')
        print("🔄 Forcing token refresh...")
    
    cached_token = cache.get('zoom_token')
    if cached_token and not force_refresh:
        print("✅ Using cached token")
        return cached_token

    try:
        print("🔑 Generating new access token...")
        
        # Create Basic Auth header
        auth_string = f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}"
        b64_auth = base64.b64encode(auth_string.encode()).decode()

        # IMPORTANT: Use account_credentials for Server-to-Server OAuth
        url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={ZOOM_ACCOUNT_ID}"
        
        headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Make the request
        response = requests.post(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Token request failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
            raise Exception(f"Token generation failed: {response.status_code} - {response.text}")

        token_data = response.json()
        access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)

        # Cache token for slightly less than expiry time
        cache.set("zoom_token", access_token, expires_in - 300)  # 5 minutes buffer
        
        logger.info(f"✅ New token generated successfully. Expires in: {expires_in} seconds")
        print(f"✅ New token generated and cached")
        
        return access_token

    except Exception as e:
        logger.error(f"Error getting Zoom token: {e}")
        raise

def verify_token_scopes(token):
    """Verify what scopes the token actually has"""
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Test user scope
        user_response = requests.get("https://api.zoom.us/v2/users/me", headers=headers)
        user_scope_ok = user_response.status_code == 200
        
        # Test meeting read scope
        meetings_response = requests.get("https://api.zoom.us/v2/users/me/meetings", headers=headers)
        read_scope_ok = meetings_response.status_code == 200
        
        # Test meeting write scope with a minimal payload
        test_meeting = {
            "topic": "Scope Verification Test - DELETE ME",
            "type": 2,
            "duration": 30
        }
        
        create_response = requests.post(
            "https://api.zoom.us/v2/users/me/meetings", 
            headers=headers, 
            json=test_meeting
        )
        
        write_scope_ok = create_response.status_code == 201
        
        # If meeting was created, delete it immediately
        if write_scope_ok:
            meeting_id = create_response.json().get('id')
            requests.delete(f"https://api.zoom.us/v2/meetings/{meeting_id}", headers=headers)
            print("✅ Test meeting created and deleted successfully")
        
        return {
            'user_scope': user_scope_ok,
            'read_scope': read_scope_ok,
            'write_scope': write_scope_ok,
            'all_scopes_ok': user_scope_ok and read_scope_ok and write_scope_ok,
            'error_details': create_response.text if not write_scope_ok else None
        }
        
    except Exception as e:
        return {
            'user_scope': False,
            'read_scope': False, 
            'write_scope': False,
            'all_scopes_ok': False,
            'error_details': str(e)
        }

def create_zoom_meeting(
    topic="Professional Meeting",
    duration=60,
    start_time=None,
    agenda="",
    force_new_token=False
):
    """
    Create a Zoom meeting with automatic token refresh if scope error occurs.
    """
    try:
        # Get token (force refresh if requested)
        token = get_zoom_access_token(force_refresh=force_new_token)
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "topic": topic,
            "type": 2,  # Scheduled meeting
            "duration": duration,
            "agenda": agenda,
            "settings": {
                "host_video": True,
                "participant_video": True,
                "waiting_room": True,
                "join_before_host": False,
                "mute_upon_entry": True,
                "approval_type": 0,
                "audio": "both",
                "auto_recording": "none",
                "enforce_login": False,
                "meeting_authentication": False,
                "use_pmi": False
            }
        }

        # Handle start_time
        if start_time:
            if isinstance(start_time, str):
                payload["start_time"] = start_time if start_time.endswith('Z') else f"{start_time}Z"
            elif isinstance(start_time, datetime):
                payload["start_time"] = start_time.isoformat() + 'Z'
        else:
            # Default start time to now + 5 minutes
            default_time = datetime.utcnow() + timedelta(minutes=5)
            payload["start_time"] = default_time.isoformat() + 'Z'

        # Create meeting
        response = requests.post(
            "https://api.zoom.us/v2/users/me/meetings",
            headers=headers,
            json=payload,
            timeout=30
        )

        # If scope error and we haven't tried refreshing token yet, try once more
        if response.status_code == 400 and "scopes" in response.text.lower() and not force_new_token:
            print("🔄 Scope error detected, refreshing token and retrying...")
            clear_zoom_token_cache()  # Clear cache
            return create_zoom_meeting(topic, duration, start_time, agenda, force_new_token=True)

        if response.status_code != 201:
            logger.error(f"Meeting creation failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
            raise Exception(f"Meeting creation failed: {response.status_code} - {response.text}")

        meeting_data = response.json()
        logger.info(f"Meeting created successfully. ID: {meeting_data.get('id')}")
        
        return meeting_data

    except Exception as e:
        logger.error(f"Error creating Zoom meeting: {e}")
        raise

def test_zoom_connection():
    """
    Enhanced test function that also verifies scopes
    """
    try:
        # Clear cache first to ensure fresh token
        clear_zoom_token_cache()
        
        token = get_zoom_access_token(force_refresh=True)
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Test user info
        response = requests.get("https://api.zoom.us/v2/users/me", headers=headers, timeout=30)
        
        if response.status_code == 200:
            user_data = response.json()
            
            # Verify scopes
            scope_verification = verify_token_scopes(token)
            
            return {
                "success": True,
                "message": "Connection successful with scope verification",
                "user_id": user_data.get("id"),
                "email": user_data.get("email"),
                "account_id": user_data.get("account_id"),
                "scopes_verified": scope_verification['all_scopes_ok'],
                "scope_details": {
                    "user_scope": "✅" if scope_verification['user_scope'] else "❌",
                    "read_scope": "✅" if scope_verification['read_scope'] else "❌", 
                    "write_scope": "✅" if scope_verification['write_scope'] else "❌"
                },
                "scope_error": scope_verification.get('error_details') if not scope_verification['all_scopes_ok'] else None
            }
        else:
            return {
                "success": False,
                "message": f"Connection test failed: {response.status_code} - {response.text}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection test error: {str(e)}"
        }

# Django management command to clear token cache
"""
# Create: zoom/management/commands/clear_zoom_cache.py

from django.core.management.base import BaseCommand
from django.core.cache import cache

class Command(BaseCommand):
    help = 'Clear Zoom token cache'

    def handle(self, *args, **options):
        cache.delete('zoom_token')
        self.stdout.write(
            self.style.SUCCESS('✅ Zoom token cache cleared successfully')
        )
"""

# Quick test function
if __name__ == "__main__":
    print("🧪 Testing Zoom connection with scope verification...")
    result = test_zoom_connection()
    
    print("\n" + "="*50)
    print("TEST RESULTS:")
    print("="*50)
    
    if result["success"]:
        print(f"✅ Connection: {result['message']}")
        print(f"📧 Email: {result['email']}")
        print(f"🆔 User ID: {result['user_id']}")
        print(f"🏢 Account ID: {result['account_id']}")
        print("\nScope Verification:")
        for scope, status in result['scope_details'].items():
            print(f"  {scope}: {status}")
        
        if result['scopes_verified']:
            print("\n🎉 ALL SCOPES WORKING! You can create meetings now.")
        else:
            print("\n⚠️ SCOPE ISSUES DETECTED!")
            if result.get('scope_error'):
                print(f"Error details: {result['scope_error']}")
    else:
        print(f"❌ Connection failed: {result['message']}")