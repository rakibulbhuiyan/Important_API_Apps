from django.test import TestCase

# Create your tests here.
# import base64
# import requests

# ZOOM_ACCOUNT_ID = "kn_lsO2oQauojuWPn78hXQ"
# ZOOM_CLIENT_ID = "NzBt8i8kTKGHLs6QIApIKQ"
# ZOOM_CLIENT_SECRET = "8UVovLYF2Y6xCinh9sD0wnmpjZhxZlaE"

# url = "https://zoom.us/oauth/token"

# # Encode client_id:client_secret in base64
# auth_str = f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}"
# b64_auth = base64.b64encode(auth_str.encode()).decode()

# headers = {
#     "Authorization": f"Basic {b64_auth}",
#     "Content-Type": "application/x-www-form-urlencoded"
# }

# # Data should be sent in the POST body
# data = {
#     "grant_type": "account_credentials",
#     "account_id": ZOOM_ACCOUNT_ID
# }

# response = requests.post(url, headers=headers, data=data)
# print(response.json())
