import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
print("Using Client ID:", CLIENT_ID)

REDIRECT_URI = "http://127.0.0.1:8888/callback"

SCOPES = "user-modify-playback-state user-read-playback-state"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPES
))

def play():
    sp.start_playback()

def pause():
    sp.pause_playback()

def next_track():
    sp.next_track()

def previous_track():
    sp.previous_track()

def set_volume(percent):
    percent = max(0, min(100, int(percent)))
    sp.volume(percent)

def get_current_track():
    current = sp.current_playback()
    if current and current["item"]:
        return current["item"]["name"], current["item"]["artists"][0]["name"]
    return None, None

if __name__ == "__main__":
    print("Testing Spotify connection...")
    name, artist = get_current_track()
    if name:
        print(f"Currently playing: {name} by {artist}")
    else:
        print("Nothing is currently playing (make sure Spotify is open and playing something)")