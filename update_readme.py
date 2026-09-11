import os
import urllib.request
import urllib.parse
import json
import base64
from collections import Counter
from datetime import datetime

def url_to_base64(image_url):
    """Downloads an image and converts it to a base64 data URI."""
    req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        img_data = response.read()
    b64_str = base64.b64encode(img_data).decode('utf-8')
    return f"data:image/jpeg;base64,{b64_str}"

def generate_spotify_svg(track_name, artist_name, cover_url):
    cover_b64 = url_to_base64(cover_url)
    
    # SVG architecture utilizing internal CSS for Dark/Light mode support
    svg_template = f"""
    <svg width="400" height="120" xmlns="http://www.w3.org/2000/svg">
      <style>
        .bg {{ fill: #ffffff; stroke: #e1e4e8; stroke-width: 1px; rx: 10px; }}
        .title {{ font: 600 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: #24292e; }}
        .text {{ font: 400 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: #586069; }}
        
        /* Automatically switch colors if the user views GitHub in Dark Mode */
        @media (prefers-color-scheme: dark) {{
          .bg {{ fill: #0d1117; stroke: #30363d; }}
          .title {{ fill: #c9d1d9; }}
          .text {{ fill: #8b949e; }}
        }}
      </style>
      
      <!-- Background Card -->
      <rect x="0" y="0" width="100%" height="100%" class="bg" />
      
      <!-- Base64 Embedded Album Cover -->
      <image href="{cover_b64}" x="15" y="15" height="90" width="90" preserveAspectRatio="xMidYMid slice" clip-path="url(#corners)" />
      
      <clipPath id="corners">
        <rect x="15" y="15" width="90" height="90" rx="8" />
      </clipPath>

      <!-- Text Elements -->
      <text x="120" y="40" class="title">Currently on Heavy Rotation</text>
      <text x="120" y="65" class="text">Track: {track_name}</text>
      <text x="120" y="85" class="text">Artist: {artist_name}</text>
    </svg>
    """
    return svg_template

def get_github_stats(token, username):
    print("\n--- FETCHING GITHUB STATS ---")
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}"}
    
    query = """
    query {
      user(login: "%s") {
        repositories(isFork: false, privacy: PUBLIC, ownerAffiliations: [OWNER], first: 100) {
          nodes {
            name
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
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
    
    for repo in repos:
        repo_name = repo['name']
        for edge in repo['languages']['edges']:
            lang_name = edge['node']['name']
            size = edge['size']
            language_bytes[lang_name] += size
            # Debug log to identify which repo is skewing the bytes
            print(f"Repo: {repo_name.ljust(25)} | Lang: {lang_name.ljust(12)} | Bytes: {size}")

    total_bytes = sum(language_bytes.values())
    print(f"Total Bytes Tracked: {total_bytes}")
    
    lang_markdown = "### 💻 Top Languages\n\n```text\n"
    for lang, size in language_bytes.most_common(5):
        percent = (size / total_bytes) * 100
        blocks = int((percent / 100) * 20)
        bar = "█" * blocks + "░" * (20 - blocks)
        lang_markdown += f"{lang.ljust(15)} {bar} {percent:.1f}%\n"
    lang_markdown += "```\n"
    
    return lang_markdown

def get_spotify_stats(client_id, client_secret, refresh_token):
    print("\n--- FETCHING SPOTIFY TOP STATS (4-WEEK WINDOW) ---")
    auth_string = f"{client_id}:{client_secret}"
    auth_base64 = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

    token_url = "https://accounts.spotify.com/api/token"
    payload = urllib.parse.urlencode({'grant_type': 'refresh_token', 'refresh_token': refresh_token}).encode('utf-8')

    req = urllib.request.Request(token_url, data=payload)
    req.add_header("Authorization", f"Basic {auth_base64}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req) as response:
            access_token = json.loads(response.read())['access_token']
    except urllib.error.HTTPError as e:
        print(f"Token Auth Failed. Ensure your refresh token has 'user-top-read' scope. Error: {e.read()}")
        return "Spotify Authentication Error"

    # Fetch Top Track
    track_url = "https://api.spotify.com/v1/me/top/tracks?time_range=short_term&limit=1"
    track_req = urllib.request.Request(track_url)
    track_req.add_header("Authorization", f"Bearer {access_token}")
    
    with urllib.request.urlopen(track_req) as response:
        top_track_data = json.loads(response.read())['items']

    # Fetch Top Artist
    artist_url = "https://api.spotify.com/v1/me/top/artists?time_range=short_term&limit=1"
    artist_req = urllib.request.Request(artist_url)
    artist_req.add_header("Authorization", f"Bearer {access_token}")
    
    with urllib.request.urlopen(artist_req) as response:
        top_artist_data = json.loads(response.read())['items']

    if not top_track_data or not top_artist_data:
        return "Not enough Spotify data for this period."

    # Extract variables
    top_track = top_track_data[0]
    top_artist = top_artist_data[0]
    cover_url = top_track['album']['images'][0]['url']
    
    # Safely fetch the genres list, defaulting to an empty list if the key is missing
    artist_genres = top_artist.get('genres', [])

    # 1. Generate the SVG string
    spotify_svg_content = generate_spotify_svg(
        track_name=top_track['name'], 
        artist_name=top_artist['name'], 
        cover_url=top_track['album']['images'][0]['url']
    )
    
    # 2. Write it to a file
    with open("spotify_stats.svg", "w", encoding="utf-8") as file:
        file.write(spotify_svg_content)


if __name__ == "__main__":
    github_token = os.environ['GH_PAT']
    spotify_client_id = os.environ['SPOTIFY_CLIENT_ID']
    spotify_client_secret = os.environ['SPOTIFY_CLIENT_SECRET']
    spotify_refresh_token = os.environ['SPOTIFY_REFRESH_TOKEN']
    
    github_user = "m-olej" 
    
    lang_md = get_github_stats(github_token, github_user)
    get_spotify_stats(spotify_client_id, spotify_client_secret, spotify_refresh_token)
    
    print("\n--- COMPILING README ---")
    with open("README.template.md", "r", encoding="utf-8") as file:
        template = file.read()

    new_readme = template.replace("{{ GITHUB_LANGS }}", lang_md)

    with open("README.md", "w", encoding="utf-8") as file:
        file.write(new_readme)
    print("Successfully wrote to README.md")
