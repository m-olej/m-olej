import os
import urllib.request
import urllib.parse
import json
import base64

client_id = os.environ['SPOTIFY_CLIENT_ID']
client_secret = os.environ['SPOTIFY_CLIENT_SECRET']
refresh_token = os.environ['SPOTIFY_REFRESH_TOKEN']

# 1. Base64 encode the client credentials
auth_string = f"{client_id}:{client_secret}"
auth_base64 = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

# 2. Request a fresh access token
token_url = "https://accounts.spotify.com/api/token"
payload = urllib.parse.urlencode({
    'grant_type': 'refresh_token',
    'refresh_token': refresh_token
}).encode('utf-8')

req = urllib.request.Request(token_url, data=payload)
req.add_header("Authorization", f"Basic {auth_base64}")
req.add_header("Content-Type", "application/x-www-form-urlencoded")

with urllib.request.urlopen(req) as response:
    token_data = json.loads(response.read())
    access_token = token_data['access_token']

# 3. Use the access_token to fetch recently played tracks!
api_url = "https://api.spotify.com/v1/me/player/recently-played?limit=50"
api_req = urllib.request.Request(api_url)
api_req.add_header("Authorization", f"Bearer {access_token}")

with urllib.request.urlopen(api_req) as api_response:
    recent_tracks = json.loads(api_response.read())
    # You now have the raw JSON to aggregate using collections.Counter
