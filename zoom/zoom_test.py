# zoom_test.py - Run this to test your Zoom configuration
import base64
import requests
import json

# Your credentials (replace with actual values)
ACCOUNT_ID = "kn_IsO2oQauojuWsPn78hXQ"
CLIENT_ID = "NOnR6IBpQbervsOYlU4KqTQ"  
CLIENT_SECRET = "6eYcZLYjWlAvOzWYS66FvbApa9kncy3n"

def test_zoom_auth():
    """Test Zoom authentication"""
    print("🔐 Testing Zoom Authentication...")
    
    try:
        # Create auth header
        auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
        b64_auth = base64.b64encode(auth_string.encode()).decode()
        
        # Request token
        url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={ACCOUNT_ID}"
        headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        response = requests.post(url, headers=headers)
        
        if response.status_code == 200:
            token_data = response.json()
            print("✅ Authentication successful!")
            print(f"   Access token length: {len(token_data['access_token'])}")
            print(f"   Token expires in: {token_data['expires_in']} seconds")
            return token_data['access_token']
        else:
            print(f"❌ Authentication failed!")
            print(f"   Status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error during authentication: {e}")
        return None

def test_user_info(token):
    """Test user info retrieval"""
    print("\n👤 Testing User Info...")
    
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get("https://api.zoom.us/v2/users/me", headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            print("✅ User info retrieved successfully!")
            print(f"   User ID: {user_data.get('id')}")
            print(f"   Email: {user_data.get('email')}")
            print(f"   Account ID: {user_data.get('account_id')}")
            print(f"   Plan Type: {user_data.get('plan_type')}")
            return True
        else:
            print(f"❌ Failed to get user info!")
            print(f"   Status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error getting user info: {e}")
        return False

def test_create_meeting(token):
    """Test meeting creation"""
    print("\n📅 Testing Meeting Creation...")
    
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        meeting_data = {
            "topic": "Test Meeting - Please Delete",
            "type": 2,  # Scheduled meeting
            "duration": 30,
            "settings": {
                "host_video": True,
                "participant_video": True,
                "waiting_room": True,
                "join_before_host": False
            }
        }
        
        response = requests.post(
            "https://api.zoom.us/v2/users/me/meetings", 
            headers=headers, 
            json=meeting_data
        )
        
        if response.status_code == 201:
            meeting_response = response.json()
            print("✅ Meeting created successfully!")
            print(f"   Meeting ID: {meeting_response.get('id')}")
            print(f"   Topic: {meeting_response.get('topic')}")
            print(f"   Join URL: {meeting_response.get('join_url')}")
            print(f"   Start URL: {meeting_response.get('start_url')[:50]}...")
            
            # Try to delete the test meeting
            delete_test_meeting(token, meeting_response.get('id'))
            return True
        else:
            print(f"❌ Failed to create meeting!")
            print(f"   Status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating meeting: {e}")
        return False

def delete_test_meeting(token, meeting_id):
    """Delete test meeting"""
    try:
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.delete(
            f"https://api.zoom.us/v2/meetings/{meeting_id}", 
            headers=headers
        )
        
        if response.status_code in [200, 204]:
            print("✅ Test meeting deleted successfully!")
        else:
            print(f"⚠️  Could not delete test meeting (ID: {meeting_id})")
            print("   Please delete it manually from your Zoom account")
            
    except Exception as e:
        print(f"⚠️  Error deleting test meeting: {e}")

def main():
    """Main test function"""
    print("🚀 Starting Zoom Configuration Test\n")
    print("=" * 50)
    
    # Test authentication
    token = test_zoom_auth()
    if not token:
        print("\n❌ Authentication failed. Please check your credentials and app configuration.")
        print("\nCommon issues:")
        print("1. Wrong Account ID, Client ID, or Client Secret")
        print("2. App not activated in Zoom Marketplace")
        print("3. Missing required scopes in app settings")
        return False
    
    # Test user info
    user_success = test_user_info(token)
    if not user_success:
        print("\n❌ User info test failed. Check app scopes.")
        return False
    
    # Test meeting creation
    meeting_success = test_create_meeting(token)
    if not meeting_success:
        print("\n❌ Meeting creation failed. Check meeting scopes.")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All tests passed! Your Zoom integration is ready!")
    print("\nYou can now:")
    print("1. Run your Django server: python manage.py runserver")
    print("2. Test the API endpoint: GET /api/zoom/test/")
    print("3. Create meetings through your application")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n" + "=" * 50)
        print("🔧 Configuration Help:")
        print("1. Go to https://marketplace.zoom.us/")
        print("2. Sign in and go to 'Develop' → 'Build App'")
        print("3. Select your app or create new 'Server-to-Server OAuth' app")
        print("4. Add these scopes:")
        print("   - meeting:write:meeting")
        print("   - meeting:read:meeting")
        print("   - user:read:user")
        print("5. Activate your app")
        print("6. Copy the correct Account ID, Client ID, and Client Secret")

# Django management command version
# Create: zoom/management/commands/test_zoom.py

"""
from django.core.management.base import BaseCommand
from django.conf import settings
import base64
import requests

class Command(BaseCommand):
    help = 'Test Zoom API configuration'

    def handle(self, *args, **options):
        self.stdout.write('Testing Zoom configuration...')
        
        try:
            # Get credentials from settings
            client_id = settings.ZOOM_CLIENT_ID
            client_secret = settings.ZOOM_CLIENT_SECRET
            account_id = settings.ZOOM_ACCOUNT_ID
            
            # Test authentication
            auth_string = f"{client_id}:{client_secret}"
            b64_auth = base64.b64encode(auth_string.encode()).decode()
            
            url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={account_id}"
            headers = {
                "Authorization": f"Basic {b64_auth}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            response = requests.post(url, headers=headers)
            
            if response.status_code == 200:
                self.stdout.write(
                    self.style.SUCCESS('✅ Zoom authentication successful!')
                )
                
                # Test user info
                token = response.json()['access_token']
                user_response = requests.get(
                    "https://api.zoom.us/v2/users/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if user_response.status_code == 200:
                    user_data = user_response.json()
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ User: {user_data.get("email")}')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('❌ Cannot get user info - check scopes')
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Authentication failed: {response.text}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {e}')
            )
"""