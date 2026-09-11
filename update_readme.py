import os
import urllib.request
import urllib.parse
import json
import base64
import html
from collections import Counter
from datetime import datetime

def url_to_base64(image_url):
    req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        img_data = response.read()
    b64_str = base64.b64encode(img_data).decode('utf-8')
    return f"data:image/jpeg;base64,{b64_str}"

def generate_spotify_svg(top_artist_name, tracks, cover_url):
    cover_b64 = url_to_base64(cover_url)
    
    # Generate the track list text elements
    track_list_svg = ""
    y_offset = 110
    
    for i, track in enumerate(tracks[:5]):
        track_name = track['name']
        artist_name = track['artists'][0]['name']
        
        # Format and truncate long text to prevent overflow
        full_text = f"{i+1}. {track_name} - {artist_name}"
        if len(full_text) > 42:
            full_text = full_text[:39] + "..."
            
        # Escape XML characters like '&'
        safe_text = html.escape(full_text)
        
        track_list_svg += f'<text x="210" y="{y_offset}" class="text">{safe_text}</text>\n'
        y_offset += 25

    safe_artist_name = html.escape(top_artist_name)

    svg_template = f"""
    <svg width="500" height="260" xmlns="http://www.w3.org/2000/svg">
      <style>
        .bg {{ fill: #ffffff; stroke: #e1e4e8; stroke-width: 1px; rx: 10px; }}
        .title {{ font: 600 16px 'Segoe UI', Ubuntu, Sans-Serif; fill: #24292e; }}
        .subtitle {{ font: 600 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: #24292e; }}
        .text {{ font: 400 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: #586069; }}
        .divider {{ stroke: #e1e4e8; stroke-width: 1px; }}
        
        /* Dark Mode Support */
        @media (prefers-color-scheme: dark) {{
          .bg {{ fill: #0d1117; stroke: #30363d; }}
          .title, .subtitle {{ fill: #c9d1d9; }}
          .text {{ fill: #8b949e; }}
          .divider {{ stroke: #30363d; }}
        }}
      </style>
      
      <!-- Background Card -->
      <rect x="0" y="0" width="100%" height="100%" class="bg" />
      
      <!-- Top Centered Artist -->
      <text x="50%" y="35" text-anchor="middle" class="title">Top Artist: {safe_artist_name}</text>
      
      <!-- Separator Line -->
      <line x1="20" y1="50" x2="480" y2="50" class="divider" />
      
      <!-- Left Cover Image (Using Track No. 1) -->
      <image href="{cover_b64}" x="30" y="70" height="150" width="150" preserveAspectRatio="xMidYMid slice" clip-path="url(#corners)" />
      <clipPath id="corners">
        <rect x="30" y="70" width="150" height="150" rx="8" />
      </clipPath>

      <!-- Right Track List -->
      <text x="210" y="85" class="subtitle">Top Tracks</text>
      {track_list_svg}
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
    
    lang_markdown = "```text\n"
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
    track_url = "https://api.spotify.com/v1/me/top/tracks?time_range=short_term&limit=5"
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

    cover_url = top_track_data[0]['album']['images'][0]['url']
    
    # 1. Generate the SVG string
    spotify_svg_content = generate_spotify_svg(
        tracks=top_track_data,
        top_artist_name=top_artist_data[0]['name'], 
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
