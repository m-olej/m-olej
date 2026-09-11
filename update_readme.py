import os
import urllib.request
import urllib.parse
import json
import base64
from collections import Counter
from datetime import datetime

# =======================================================
# 1. GitHub Language Aggregation (GraphQL)
# =======================================================
def get_github_stats(token, username):
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}"}
    
    # GraphQL query to fetch the last 100 repositories and their language byte size
    query = """
    query {
      user(login: "%s") {
        repositories(isFork: false, privacy: PUBLIC, ownerAffiliations: [OWNER], first: 100) {
          nodes {
            languages(first: 100, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                }
              }
            }
          }
        }
      }
    }
    """ % username

    req = urllib.request.Request(url, data=json.dumps({"query": query}).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read())

    language_bytes = Counter()
    repos = data['data']['user']['repositories']['nodes']
    
    # Aggregate total byte size per language
    for repo in repos:
        for edge in repo['languages']['edges']:
            language_bytes[edge['node']['name']] += edge['size']

    total_bytes = sum(language_bytes.values())
    
    # Generate Markdown Progress Bars
    lang_markdown = "### 💻 Top Languages\n\n```text\n"
    for lang, size in language_bytes.most_common(5):
        percent = (size / total_bytes) * 100
        blocks = int((percent / 100) * 20)
        bar = "█" * blocks + "░" * (20 - blocks)
        lang_markdown += f"{lang.ljust(15)} {bar} {percent:.1f}%\n"
    lang_markdown += "```\n"
    
    return lang_markdown

# =======================================================
# 2. Spotify Stats (Recently Played)
# =======================================================
def get_spotify_stats(client_id, client_secret, refresh_token):
    # Base64 encode the client credentials
    auth_string = f"{client_id}:{client_secret}"
    auth_base64 = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

    # Request a fresh access token
    token_url = "https://accounts.spotify.com/api/token"
    payload = urllib.parse.urlencode({'grant_type': 'refresh_token', 'refresh_token': refresh_token}).encode('utf-8')

    req = urllib.request.Request(token_url, data=payload)
    req.add_header("Authorization", f"Basic {auth_base64}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req) as response:
        access_token = json.loads(response.read())['access_token']

    # Fetch recently played tracks
    api_url = "https://api.spotify.com/v1/me/player/recently-played?limit=50"
    api_req = urllib.request.Request(api_url)
    api_req.add_header("Authorization", f"Bearer {access_token}")

    with urllib.request.urlopen(api_req) as api_response:
        tracks = json.loads(api_response.read())['items']

    if not tracks:
        return "No recent tracks found."

    # Analyze data with Counter
    latest_track = tracks[0]['track']
    artists = Counter([track['track']['artists'][0]['name'] for track in tracks])
    albums = Counter([track['track']['album']['name'] for track in tracks])
    
    top_artist = artists.most_common(1)[0][0]
    top_album = albums.most_common(1)[0][0]

    # Markdown formatting with image tag for the latest track cover
    cover_url = latest_track['album']['images'][0]['url']
    spotify_markdown = f"""### 🎧 Weekly Spotify Stats
<div style="display: flex; align-items: center;">
    <img src="{cover_url}" width="100" style="border-radius: 10px; margin-right: 15px;" />
    <div>
        <strong>Latest Track:</strong> {latest_track['name']} by {latest_track['artists'][0]['name']}<br/>
        <strong>Top Artist This Week:</strong> {top_artist}<br/>
        <strong>Top Album This Week:</strong> {top_album}
    </div>
</div>
"""
    return spotify_markdown

# =======================================================
# Engine Execution
# =======================================================
if __name__ == "__main__":
    # Fetch environment variables injected by GitHub Actions
    github_token = os.environ['GH_PAT'] 
    spotify_client_id = os.environ['SPOTIFY_CLIENT_ID']
    spotify_client_secret = os.environ['SPOTIFY_CLIENT_SECRET']
    spotify_refresh_token = os.environ['SPOTIFY_REFRESH_TOKEN']
    
    github_user = "m-olej" # Replace with your username
    
    # Generate Markdown blocks
    lang_md = get_github_stats(github_token, github_user)
    spotify_md = get_spotify_stats(spotify_client_id, spotify_client_secret, spotify_refresh_token)
    
    # Compile the final template
    with open("README.template.md", "r", encoding="utf-8") as file:
        template = file.read()

    new_readme = template.replace("{{ GITHUB_LANGS }}", lang_md)
    new_readme = new_readme.replace("{{ SPOTIFY_STATS }}", spotify_md)
    new_readme = new_readme.replace("{{ RSS_FEED }}", rss_md)

    with open("README.md", "w", encoding="utf-8") as file:
        file.write(new_readme)
