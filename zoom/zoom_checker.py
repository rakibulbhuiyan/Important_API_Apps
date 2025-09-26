# scope_checker.py - Run this to verify what scopes your token has
import base64
import requests
import json

# Your credentials
ZOOM_CLIENT_ID = "NzBt8i8kTKGHLs6QIApIKQ"
ZOOM_CLIENT_SECRET = "8UVovLYF2Y6xCinh9sD0wnmpjZhxZlaE"
ZOOM_ACCOUNT_ID = "kn_IsO2oQauojuWPn78hXQ"

def check_token_scopes():
    """Check what scopes your access token actually has"""
    try:
        # Get token
        auth_string = f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}"
        b64_auth = base64.b64encode(auth_string.encode()).decode()

        url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={ZOOM_ACCOUNT_ID}"
        headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        print("🔑 Getting access token...")
        response = requests.post(url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Token request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        token_data = response.json()
        access_token = token_data["access_token"]
        print(f"✅ Token obtained successfully")
        
        # Check token info (this endpoint shows scopes if available)
        token_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Try to get user info (requires user:read scope)
        print("\n👤 Testing user:read scope...")
        user_response = requests.get("https://api.zoom.us/v2/users/me", headers=token_headers)
        
        if user_response.status_code == 200:
            user_data = user_response.json()
            print(f"✅ User scope works: {user_data.get('email')}")
        else:
            print(f"❌ User scope failed: {user_response.status_code} - {user_response.text}")
        
        # Try to list meetings (requires meeting:read scope)  
        print("\n📋 Testing meeting:read scope...")
        meetings_response = requests.get("https://api.zoom.us/v2/users/me/meetings", headers=token_headers)
        
        if meetings_response.status_code == 200:
            meetings_data = meetings_response.json()
            print(f"✅ Meeting read scope works: Found {meetings_data.get('total_records', 0)} meetings")
        else:
            print(f"❌ Meeting read scope failed: {meetings_response.status_code} - {meetings_response.text}")
        
        # Try to create a test meeting (requires meeting:write scope)
        print("\n📅 Testing meeting:write scope...")
        test_meeting = {
            "topic": "Scope Test Meeting - DELETE ME",
            "type": 2,
            "duration": 30,
            "settings": {
                "host_video": True,
                "participant_video": True
            }
        }
        
        create_response = requests.post(
            "https://api.zoom.us/v2/users/me/meetings", 
            headers=token_headers, 
            json=test_meeting
        )
        
        if create_response.status_code == 201:
            meeting_data = create_response.json()
            print(f"✅ Meeting write scope works: Created meeting {meeting_data.get('id')}")
            
            # Try to delete the test meeting
            delete_response = requests.delete(
                f"https://api.zoom.us/v2/meetings/{meeting_data.get('id')}", 
                headers=token_headers
            )
            if delete_response.status_code in [200, 204]:
                print("✅ Test meeting deleted successfully")
            else:
                print(f"⚠️ Could not delete test meeting: {delete_response.status_code}")
                
        else:
            print(f"❌ Meeting write scope failed: {create_response.status_code}")
            print(f"Response: {create_response.text}")
            
            # Parse error for scope information
            try:
                error_data = create_response.json()
                if "scopes" in error_data.get("message", "").lower():
                    print("\n🔍 SCOPE ISSUE DETECTED!")
                    print("Your app is missing required scopes.")
                    print("Please add these scopes in your Zoom app:")
                    print("- meeting:write:meeting")
                    print("- meeting:write:meeting:admin") 
                    print("- meeting:read:meeting:admin")
                    print("- user:read:user:admin")
            except:
                pass
        
        return True
        
    except Exception as e:
        print(f"❌ Error during scope check: {e}")
        return False

def main():
    print("🔍 Checking Zoom Token Scopes")
    print("=" * 50)
    
    success = check_token_scopes()
    
    if success:
        print("\n" + "=" * 50)
        print("✅ Scope check completed!")
        print("\nIf you saw any ❌ errors above, you need to:")
        print("1. Go to https://marketplace.zoom.us/")
        print("2. Edit your app")
        print("3. Go to 'Scopes' tab")
        print("4. Add the missing scopes")
        print("5. Save and re-activate your app")
    else:
        print("\n❌ Scope check failed. Please verify your credentials.")

if __name__ == "__main__":
    main()