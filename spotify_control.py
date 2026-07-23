import os

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth


# --------------------------------------------------
# LOAD SPOTIFY CREDENTIALS FROM .env
# --------------------------------------------------

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

REDIRECT_URI = "http://127.0.0.1:8888/callback"

SCOPES = (
    "user-modify-playback-state "
    "user-read-playback-state "
    "user-read-currently-playing"
)


# --------------------------------------------------
# CHECK ENVIRONMENT VARIABLES
# --------------------------------------------------

if not CLIENT_ID:
    raise ValueError(
        "SPOTIFY_CLIENT_ID was not found. "
        "Check your .env file."
    )

if not CLIENT_SECRET:
    raise ValueError(
        "SPOTIFY_CLIENT_SECRET was not found. "
        "Check your .env file."
    )


# --------------------------------------------------
# CREATE SPOTIFY CLIENT
# --------------------------------------------------

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
        open_browser=True,
        cache_path=".spotify_cache"
    )
)


# --------------------------------------------------
# PLAYBACK CONTROLS
# --------------------------------------------------

def play():
    """Resume Spotify playback."""

    try:
        sp.start_playback()

    except spotipy.SpotifyException as error:
        print("Spotify play error:", error)


def pause():
    """Pause Spotify playback."""

    try:
        sp.pause_playback()

    except spotipy.SpotifyException as error:
        print("Spotify pause error:", error)


def next_track():
    """Skip to the next Spotify track."""

    try:
        sp.next_track()

    except spotipy.SpotifyException as error:
        print("Spotify next-track error:", error)


def previous_track():
    """Return to the previous Spotify track."""

    try:
        sp.previous_track()

    except spotipy.SpotifyException as error:
        print("Spotify previous-track error:", error)


def set_volume(percent):
    """Set Spotify volume between 0 and 100."""

    try:
        percent = int(percent)
        percent = max(0, min(100, percent))

        sp.volume(percent)

    except (TypeError, ValueError) as error:
        print("Invalid Spotify volume:", error)

    except spotipy.SpotifyException as error:
        print("Spotify volume error:", error)


# --------------------------------------------------
# CURRENT PLAYBACK INFORMATION
# --------------------------------------------------

def get_current_playback():
    """
    Return the complete Spotify playback dictionary.

    spotify_screen.py uses this for:
    - song title
    - artist
    - album name
    - album cover
    - progress
    - duration
    - playing/paused status
    """

    try:
        return sp.current_playback()

    except spotipy.SpotifyException as error:
        print("Spotify playback-state error:", error)
        return None


def get_current_track():
    """
    Return only the current song name and artist.

    Example:
        song, artist = get_current_track()
    """

    current = get_current_playback()

    if not current:
        return None, None

    item = current.get("item")

    if not item:
        return None, None

    song_name = item.get("name")

    artists = item.get("artists", [])

    artist_name = ", ".join(
        artist.get("name", "")
        for artist in artists
        if artist.get("name")
    )

    return song_name, artist_name or None


def is_playing():
    """Return True when Spotify is currently playing."""

    current = get_current_playback()

    if not current:
        return False

    return bool(current.get("is_playing", False))


def get_active_device():
    """Return information about the active Spotify device."""

    current = get_current_playback()

    if not current:
        return None

    return current.get("device")


# --------------------------------------------------
# CONNECTION TEST
# --------------------------------------------------

if __name__ == "__main__":
    print("Testing Spotify connection...")

    try:
        playback = get_current_playback()

        if not playback:
            print(
                "Spotify connected, but no active playback was found.\n"
                "Open Spotify, play a song, and run this file again."
            )

        else:
            song, artist = get_current_track()
            device = playback.get("device", {})
            device_name = device.get("name", "Unknown device")

            if song:
                print(f"Current track: {song}")
                print(f"Artist: {artist}")
                print(f"Device: {device_name}")
                print(
                    "Status:",
                    "Playing"
                    if playback.get("is_playing")
                    else "Paused"
                )

            else:
                print(
                    "Spotify is connected, but nothing is currently playing."
                )

    except Exception as error:
        print("Spotify connection test failed:", error)