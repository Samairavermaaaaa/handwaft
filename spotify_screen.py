import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import time
import math
import threading
from io import BytesIO

import requests
from PIL import Image
import customtkinter as ctk

import spotify_control as spotify


# ---------------------------------------------------------
# COLOURS
# ---------------------------------------------------------

BACKGROUND = "#0a0e16"
CARD_BACKGROUND = "#141a24"
CARD_BORDER = "#242d3a"

ACCENT = "#22d3ee"
ACCENT_HOVER = "#0891b2"
ACCENT_DIM = "#0e2a30"

TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#8b95a3"
SPOTIFY_GREEN = "#1ed760"


class SpotifyScreen:
    def __init__(self, parent_frame, on_back):
        self.parent_frame = parent_frame
        self.on_back = on_back

        self.running = True
        self.is_paused = False

        self.volume_locked = False
        self.volume_mode = False

        self.current_album_url = None
        self.album_photo = None
        self.song_refresh_running = False

        # -------------------------------------------------
        # GESTURE SETTINGS
        # -------------------------------------------------

        self.FIST_FRAMES_NEEDED = 3
        self.THUMB_FRAMES_NEEDED = 3
        self.LOCK_FRAMES_NEEDED = 4

        self.ACTION_COOLDOWN = 0.55
        self.last_action_time = 0

        self.fist_frames = 0
        self.thumbs_up_frames = 0
        self.thumbs_down_frames = 0
        self.two_finger_frames = 0
        self.three_finger_frames = 0
        self.pinch_frames = 0

        self.action_locked = False

        self.PINCH_START_THRESHOLD = 0.30
        self.PINCH_RELEASE_THRESHOLD = 0.48
        self.PINCH_START_FRAMES = 4

        self.VOLUME_LEFT_X = 0.18
        self.VOLUME_RIGHT_X = 0.82
        self.VOLUME_STEP = 5
        self.VOLUME_SEND_INTERVAL = 0.18

        self.smoothed_volume = None
        self.last_volume_sent = -1
        self.last_volume_send_time = 0
        self.current_volume = 0

        # -------------------------------------------------
        # MAIN CONTAINER
        # -------------------------------------------------

        self.container = ctk.CTkFrame(
            parent_frame,
            fg_color=BACKGROUND,
            corner_radius=0
        )

        self.container.pack(
            fill="both",
            expand=True
        )

        self.container.grid_rowconfigure(1, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # -------------------------------------------------
        # HEADER
        # -------------------------------------------------

        self.header = ctk.CTkFrame(
            self.container,
            fg_color="transparent",
            height=70
        )

        self.header.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=24,
            pady=(16, 8)
        )

        self.header.grid_columnconfigure(1, weight=1)

        back_btn = ctk.CTkButton(
            self.header,
            text="← Back",
            width=100,
            height=38,
            corner_radius=19,
            fg_color=CARD_BACKGROUND,
            hover_color=CARD_BORDER,
            border_width=1,
            border_color=CARD_BORDER,
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 13, "bold"),
            command=self.stop
        )

        back_btn.grid(
            row=0,
            column=0,
            sticky="w"
        )

        title_frame = ctk.CTkFrame(
            self.header,
            fg_color="transparent"
        )

        title_frame.grid(
            row=0,
            column=1
        )

        ctk.CTkLabel(
            title_frame,
            text="Spotify Gesture Control",
            font=("Segoe UI", 23, "bold"),
            text_color=TEXT_PRIMARY
        ).pack()

        ctk.CTkLabel(
            title_frame,
            text="Control your music using hand gestures",
            font=("Segoe UI", 12),
            text_color=TEXT_SECONDARY
        ).pack(pady=(2, 0))

        self.connection_badge = ctk.CTkLabel(
            self.header,
            text="●  Checking Spotify",
            width=155,
            height=34,
            corner_radius=17,
            fg_color=ACCENT_DIM,
            text_color=ACCENT,
            font=("Segoe UI", 11, "bold")
        )

        self.connection_badge.grid(
            row=0,
            column=2,
            sticky="e"
        )

        # -------------------------------------------------
        # MAIN CONTENT AREA
        # -------------------------------------------------

        self.content = ctk.CTkFrame(
            self.container,
            fg_color="transparent"
        )

        self.content.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=24,
            pady=(4, 24)
        )

        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_columnconfigure(1, weight=0)

        self.build_camera_section()
        self.build_now_playing_sidebar()

        # -------------------------------------------------
        # MEDIAPIPE
        # -------------------------------------------------

        BaseOptions = python.BaseOptions
        HandLandmarker = vision.HandLandmarker
        HandLandmarkerOptions = vision.HandLandmarkerOptions
        VisionRunningMode = vision.RunningMode

        options = HandLandmarkerOptions(
            base_options=BaseOptions(
                model_asset_path="hand_landmarker.task"
            ),
            running_mode=VisionRunningMode.VIDEO,
            num_hands=1
        )

        self.landmarker = HandLandmarker.create_from_options(options)

        # -------------------------------------------------
        # CAMERA
        # -------------------------------------------------

        self.cap = cv2.VideoCapture(
            0,
            cv2.CAP_DSHOW
        )

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.frame_index = 0

        if not self.cap.isOpened():
            self.camera_status_label.configure(
                text="Camera could not be opened",
                text_color="#ef4444"
            )

        # Start updates
        self.update_frame()
        self.refresh_spotify_sidebar()

    # =====================================================
    # UI BUILDERS
    # =====================================================

    def build_camera_section(self):
        self.camera_card = ctk.CTkFrame(
            self.content,
            fg_color=CARD_BACKGROUND,
            corner_radius=20,
            border_width=1,
            border_color=CARD_BORDER
        )

        self.camera_card.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 16)
        )

        self.camera_card.grid_rowconfigure(1, weight=1)
        self.camera_card.grid_columnconfigure(0, weight=1)

        camera_header = ctk.CTkFrame(
            self.camera_card,
            fg_color="transparent"
        )

        camera_header.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=20,
            pady=(18, 12)
        )

        camera_header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            camera_header,
            text="LIVE CAMERA",
            font=("Segoe UI", 12, "bold"),
            text_color=ACCENT
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.camera_status_label = ctk.CTkLabel(
            camera_header,
            text="● Camera active",
            font=("Segoe UI", 11),
            text_color=SPOTIFY_GREEN
        )

        self.camera_status_label.grid(
            row=0,
            column=1,
            sticky="e"
        )

        self.video_wrapper = ctk.CTkFrame(
            self.camera_card,
            fg_color="#05080d",
            corner_radius=14
        )

        self.video_wrapper.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=18,
            pady=(0, 14)
        )

        self.video_label = ctk.CTkLabel(
            self.video_wrapper,
            text="Starting camera...",
            text_color=TEXT_SECONDARY,
            font=("Segoe UI", 14)
        )

        self.video_label.pack(
            fill="both",
            expand=True,
            padx=6,
            pady=6
        )

        self.gesture_status = ctk.CTkLabel(
            self.camera_card,
            text="✋  Show your hand to begin",
            height=44,
            corner_radius=14,
            fg_color=ACCENT_DIM,
            text_color=ACCENT,
            font=("Segoe UI", 13, "bold")
        )

        self.gesture_status.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 18)
        )

    def build_now_playing_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self.content,
            width=300,
            fg_color=CARD_BACKGROUND,
            corner_radius=20,
            border_width=1,
            border_color=CARD_BORDER
        )

        self.sidebar.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text="NOW PLAYING",
            font=("Segoe UI", 12, "bold"),
            text_color=ACCENT
        ).pack(
            pady=(24, 18)
        )

        self.album_container = ctk.CTkFrame(
            self.sidebar,
            width=220,
            height=220,
            corner_radius=18,
            fg_color="#0d131c"
        )

        self.album_container.pack(
            padx=38
        )

        self.album_container.pack_propagate(False)

        self.album_label = ctk.CTkLabel(
            self.album_container,
            text="♫",
            font=("Segoe UI", 70, "bold"),
            text_color=TEXT_SECONDARY
        )

        self.album_label.pack(
            fill="both",
            expand=True
        )

        self.song_title_label = ctk.CTkLabel(
            self.sidebar,
            text="Nothing playing",
            wraplength=250,
            justify="center",
            font=("Segoe UI", 19, "bold"),
            text_color=TEXT_PRIMARY
        )

        self.song_title_label.pack(
            padx=22,
            pady=(20, 4)
        )

        self.artist_label = ctk.CTkLabel(
            self.sidebar,
            text="Open Spotify and play a song",
            wraplength=250,
            justify="center",
            font=("Segoe UI", 13),
            text_color=TEXT_SECONDARY
        )

        self.artist_label.pack(
            padx=22
        )

        self.album_name_label = ctk.CTkLabel(
            self.sidebar,
            text="",
            wraplength=250,
            justify="center",
            font=("Segoe UI", 11),
            text_color="#667085"
        )

        self.album_name_label.pack(
            padx=22,
            pady=(3, 0)
        )

        self.progress_bar = ctk.CTkProgressBar(
            self.sidebar,
            width=245,
            height=7,
            corner_radius=4,
            fg_color="#29313d",
            progress_color=SPOTIFY_GREEN
        )

        self.progress_bar.pack(
            pady=(24, 5)
        )

        self.progress_bar.set(0)

        times_frame = ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent",
            width=245
        )

        times_frame.pack()

        times_frame.pack_propagate(False)

        self.current_time_label = ctk.CTkLabel(
            times_frame,
            text="0:00",
            font=("Segoe UI", 10),
            text_color=TEXT_SECONDARY
        )

        self.current_time_label.pack(
            side="left"
        )

        self.duration_label = ctk.CTkLabel(
            times_frame,
            text="0:00",
            font=("Segoe UI", 10),
            text_color=TEXT_SECONDARY
        )

        self.duration_label.pack(
            side="right"
        )

        controls_frame = ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent"
        )

        controls_frame.pack(
            pady=(22, 18)
        )

        self.previous_button = ctk.CTkButton(
            controls_frame,
            text="⏮",
            width=52,
            height=42,
            corner_radius=21,
            fg_color="transparent",
            hover_color=ACCENT_DIM,
            border_width=1,
            border_color=CARD_BORDER,
            font=("Segoe UI Symbol", 18),
            command=self.previous_song_button
        )

        self.previous_button.grid(
            row=0,
            column=0,
            padx=5
        )

        self.play_pause_button = ctk.CTkButton(
            controls_frame,
            text="▶",
            width=60,
            height=60,
            corner_radius=30,
            fg_color=SPOTIFY_GREEN,
            hover_color="#17b84f",
            text_color="#04110a",
            font=("Segoe UI Symbol", 21, "bold"),
            command=self.toggle_playback_button
        )

        self.play_pause_button.grid(
            row=0,
            column=1,
            padx=7
        )

        self.next_button = ctk.CTkButton(
            controls_frame,
            text="⏭",
            width=52,
            height=42,
            corner_radius=21,
            fg_color="transparent",
            hover_color=ACCENT_DIM,
            border_width=1,
            border_color=CARD_BORDER,
            font=("Segoe UI Symbol", 18),
            command=self.next_song_button
        )

        self.next_button.grid(
            row=0,
            column=2,
            padx=5
        )

        self.playback_status_label = ctk.CTkLabel(
            self.sidebar,
            text="Waiting for Spotify playback",
            font=("Segoe UI", 11),
            text_color=TEXT_SECONDARY
        )

        self.playback_status_label.pack(
            pady=(0, 15)
        )

        gesture_info = ctk.CTkFrame(
            self.sidebar,
            fg_color="#101722",
            corner_radius=14,
            border_width=1,
            border_color=CARD_BORDER
        )

        gesture_info.pack(
            fill="x",
            padx=18,
            pady=(0, 18)
        )

        ctk.CTkLabel(
            gesture_info,
            text="GESTURE SHORTCUTS",
            font=("Segoe UI", 10, "bold"),
            text_color=ACCENT
        ).pack(
            anchor="w",
            padx=14,
            pady=(12, 7)
        )

        gestures = [
            "✊  Play / Pause",
            "👍  Next track",
            "👎  Previous track",
            "🤏  Adjust volume"
        ]

        for gesture in gestures:
            ctk.CTkLabel(
                gesture_info,
                text=gesture,
                font=("Segoe UI", 11),
                text_color=TEXT_SECONDARY
            ).pack(
                anchor="w",
                padx=14,
                pady=2
            )

        ctk.CTkLabel(
            gesture_info,
            text=""
        ).pack(pady=3)

    # =====================================================
    # SPOTIFY SIDEBAR
    # =====================================================

    def get_playback_data(self):
        """
        Supports different possible function names inside spotify_control.py.

        Recommended function in spotify_control.py:
            get_current_playback()
        """

        possible_functions = [
            "get_current_playback",
            "current_playback",
            "get_playback",
            "get_current_track",
            "currently_playing"
        ]

        for function_name in possible_functions:
            playback_function = getattr(
                spotify,
                function_name,
                None
            )

            if callable(playback_function):
                return playback_function()

        return None

    def refresh_spotify_sidebar(self):
        if not self.running:
            return

        if not self.song_refresh_running:
            self.song_refresh_running = True

            thread = threading.Thread(
                target=self.fetch_spotify_data,
                daemon=True
            )

            thread.start()

        self.container.after(
            2000,
            self.refresh_spotify_sidebar
        )

    def fetch_spotify_data(self):
        try:
            playback = self.get_playback_data()

            if self.running:
                self.container.after(
                    0,
                    lambda data=playback: self.update_sidebar_ui(data)
                )

        except Exception as error:
            print(f"Spotify sidebar error: {error}")

            if self.running:
                self.container.after(
                    0,
                    lambda: self.show_spotify_error(
                        "Could not read Spotify playback"
                    )
                )

        finally:
            self.song_refresh_running = False

    def update_sidebar_ui(self, playback):
        if not self.running:
            return

        if not playback:
            self.show_no_song()
            return

        try:
            # Supports a direct simplified dictionary
            if "item" not in playback:
                self.update_from_simple_playback(playback)
                return

            track = playback.get("item")

            if not track:
                self.show_no_song()
                return

            song_name = track.get(
                "name",
                "Unknown song"
            )

            artists_data = track.get(
                "artists",
                []
            )

            artists = ", ".join(
                artist.get("name", "")
                for artist in artists_data
                if artist.get("name")
            )

            if not artists:
                artists = "Unknown artist"

            album = track.get(
                "album",
                {}
            )

            album_name = album.get(
                "name",
                ""
            )

            album_images = album.get(
                "images",
                []
            )

            album_url = None

            if album_images:
                album_url = album_images[0].get("url")

            progress_ms = playback.get(
                "progress_ms",
                0
            ) or 0

            duration_ms = track.get(
                "duration_ms",
                0
            ) or 0

            is_playing = playback.get(
                "is_playing",
                False
            )

            self.apply_track_information(
                song_name=song_name,
                artists=artists,
                album_name=album_name,
                album_url=album_url,
                progress_ms=progress_ms,
                duration_ms=duration_ms,
                is_playing=is_playing
            )

        except Exception as error:
            print(f"Invalid Spotify playback response: {error}")
            self.show_spotify_error("Invalid playback information")

    def update_from_simple_playback(self, playback):
        song_name = (
            playback.get("song")
            or playback.get("track")
            or playback.get("name")
            or "Unknown song"
        )

        artists = (
            playback.get("artist")
            or playback.get("artists")
            or "Unknown artist"
        )

        if isinstance(artists, list):
            artists = ", ".join(str(artist) for artist in artists)

        album_name = playback.get(
            "album",
            ""
        )

        album_url = (
            playback.get("album_url")
            or playback.get("image_url")
            or playback.get("cover")
        )

        progress_ms = playback.get(
            "progress_ms",
            playback.get("progress", 0)
        ) or 0

        duration_ms = playback.get(
            "duration_ms",
            playback.get("duration", 0)
        ) or 0

        is_playing = playback.get(
            "is_playing",
            not playback.get("is_paused", False)
        )

        self.apply_track_information(
            song_name=song_name,
            artists=artists,
            album_name=album_name,
            album_url=album_url,
            progress_ms=progress_ms,
            duration_ms=duration_ms,
            is_playing=is_playing
        )

    def apply_track_information(
        self,
        song_name,
        artists,
        album_name,
        album_url,
        progress_ms,
        duration_ms,
        is_playing
    ):
        self.song_title_label.configure(
            text=song_name
        )

        self.artist_label.configure(
            text=artists
        )

        self.album_name_label.configure(
            text=album_name
        )

        progress = 0

        if duration_ms > 0:
            progress = progress_ms / duration_ms

        progress = self.clamp(
            progress,
            0,
            1
        )

        self.progress_bar.set(progress)

        self.current_time_label.configure(
            text=self.format_time(progress_ms)
        )

        self.duration_label.configure(
            text=self.format_time(duration_ms)
        )

        self.is_paused = not is_playing

        if is_playing:
            self.play_pause_button.configure(
                text="⏸"
            )

            self.playback_status_label.configure(
                text="Playing on Spotify",
                text_color=SPOTIFY_GREEN
            )

            self.connection_badge.configure(
                text="●  Spotify connected",
                text_color=SPOTIFY_GREEN,
                fg_color="#10271a"
            )

        else:
            self.play_pause_button.configure(
                text="▶"
            )

            self.playback_status_label.configure(
                text="Spotify playback paused",
                text_color=TEXT_SECONDARY
            )

            self.connection_badge.configure(
                text="●  Spotify connected",
                text_color=SPOTIFY_GREEN,
                fg_color="#10271a"
            )

        if album_url and album_url != self.current_album_url:
            self.current_album_url = album_url
            self.load_album_art(album_url)

    def load_album_art(self, image_url):
        def download_image():
            try:
                response = requests.get(
                    image_url,
                    timeout=10
                )

                response.raise_for_status()

                image = Image.open(
                    BytesIO(response.content)
                ).convert("RGB")

                image = image.resize(
                    (220, 220),
                    Image.Resampling.LANCZOS
                )

                if self.running:
                    self.container.after(
                        0,
                        lambda loaded_image=image: self.set_album_art(
                            loaded_image
                        )
                    )

            except Exception as error:
                print(f"Album artwork error: {error}")

        threading.Thread(
            target=download_image,
            daemon=True
        ).start()

    def set_album_art(self, image):
        if not self.running:
            return

        self.album_photo = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=(220, 220)
        )

        self.album_label.configure(
            image=self.album_photo,
            text=""
        )

    def show_no_song(self):
        self.song_title_label.configure(
            text="Nothing playing"
        )

        self.artist_label.configure(
            text="Open Spotify and play a song"
        )

        self.album_name_label.configure(
            text=""
        )

        self.progress_bar.set(0)

        self.current_time_label.configure(
            text="0:00"
        )

        self.duration_label.configure(
            text="0:00"
        )

        self.play_pause_button.configure(
            text="▶"
        )

        self.playback_status_label.configure(
            text="No active Spotify playback",
            text_color=TEXT_SECONDARY
        )

        self.connection_badge.configure(
            text="●  Spotify idle",
            text_color=ACCENT,
            fg_color=ACCENT_DIM
        )

    def show_spotify_error(self, message):
        self.connection_badge.configure(
            text="●  Spotify unavailable",
            text_color="#f87171",
            fg_color="#32171a"
        )

        self.playback_status_label.configure(
            text=message,
            text_color="#f87171"
        )

    @staticmethod
    def format_time(milliseconds):
        try:
            total_seconds = int(milliseconds) // 1000
            minutes = total_seconds // 60
            seconds = total_seconds % 60

            return f"{minutes}:{seconds:02d}"

        except (TypeError, ValueError):
            return "0:00"

    # =====================================================
    # SIDEBAR BUTTON CONTROLS
    # =====================================================

    def toggle_playback_button(self):
        try:
            if self.is_paused:
                spotify.play()
                self.is_paused = False

                self.play_pause_button.configure(
                    text="⏸"
                )

            else:
                spotify.pause()
                self.is_paused = True

                self.play_pause_button.configure(
                    text="▶"
                )

            self.container.after(
                400,
                self.refresh_spotify_sidebar_once
            )

        except Exception as error:
            print(f"Play/pause button error: {error}")
            self.show_spotify_error("Playback command failed")

    def next_song_button(self):
        try:
            spotify.next_track()

            self.container.after(
                700,
                self.refresh_spotify_sidebar_once
            )

        except Exception as error:
            print(f"Next button error: {error}")
            self.show_spotify_error("Next-track command failed")

    def previous_song_button(self):
        try:
            spotify.previous_track()

            self.container.after(
                700,
                self.refresh_spotify_sidebar_once
            )

        except Exception as error:
            print(f"Previous button error: {error}")
            self.show_spotify_error("Previous-track command failed")

    def refresh_spotify_sidebar_once(self):
        if not self.running or self.song_refresh_running:
            return

        self.song_refresh_running = True

        threading.Thread(
            target=self.fetch_spotify_data,
            daemon=True
        ).start()

    # =====================================================
    # GESTURE HELPERS
    # =====================================================

    @staticmethod
    def clamp(value, minimum, maximum):
        return max(
            minimum,
            min(value, maximum)
        )

    @staticmethod
    def point_distance(p1, p2):
        return math.sqrt(
            (p1.x - p2.x) ** 2
            + (p1.y - p2.y) ** 2
        )

    def palm_size(self, hand):
        return max(
            self.point_distance(
                hand[0],
                hand[9]
            ),
            0.01
        )

    def normalized_distance(
        self,
        hand,
        index_1,
        index_2
    ):
        return (
            self.point_distance(
                hand[index_1],
                hand[index_2]
            )
            / self.palm_size(hand)
        )

    @staticmethod
    def finger_extended(
        hand,
        tip,
        pip,
        mcp
    ):
        return (
            hand[tip].y < hand[pip].y - 0.01
            and hand[pip].y < hand[mcp].y + 0.04
        )

    def index_extended(self, hand):
        return self.finger_extended(
            hand,
            8,
            6,
            5
        )

    def middle_extended(self, hand):
        return self.finger_extended(
            hand,
            12,
            10,
            9
        )

    def ring_extended(self, hand):
        return self.finger_extended(
            hand,
            16,
            14,
            13
        )

    def pinky_extended(self, hand):
        return self.finger_extended(
            hand,
            20,
            18,
            17
        )

    def index_curled(self, hand):
        return not self.index_extended(hand)

    def middle_curled(self, hand):
        return not self.middle_extended(hand)

    def ring_curled(self, hand):
        return not self.ring_extended(hand)

    def pinky_curled(self, hand):
        return not self.pinky_extended(hand)

    def closed_finger_count(self, hand):
        return sum([
            self.index_curled(hand),
            self.middle_curled(hand),
            self.ring_curled(hand),
            self.pinky_curled(hand)
        ])

    def detect_thumbs_up(self, hand):
        thumb_up = (
            hand[4].y < hand[3].y
            and hand[4].y < hand[2].y
            and hand[4].y < hand[5].y
        )

        thumb_separated = (
            self.normalized_distance(
                hand,
                4,
                9
            ) > 0.62
        )

        return (
            thumb_up
            and thumb_separated
            and self.closed_finger_count(hand) >= 3
        )

    def detect_thumbs_down(self, hand):
        thumb_down = (
            hand[4].y > hand[3].y
            and hand[4].y > hand[2].y
            and hand[4].y > hand[5].y
        )

        thumb_separated = (
            self.normalized_distance(
                hand,
                4,
                9
            ) > 0.62
        )

        return (
            thumb_down
            and thumb_separated
            and self.closed_finger_count(hand) >= 3
        )

    def detect_fist(self, hand):
        return self.closed_finger_count(hand) >= 3

    def detect_two_fingers(self, hand):
        return (
            self.index_extended(hand)
            and self.middle_extended(hand)
            and self.ring_curled(hand)
            and self.pinky_curled(hand)
        )

    def detect_three_fingers(self, hand):
        return (
            self.index_extended(hand)
            and self.middle_extended(hand)
            and self.ring_extended(hand)
            and self.pinky_curled(hand)
        )

    def get_pinch_distance(self, hand):
        return self.normalized_distance(
            hand,
            4,
            8
        )

    @staticmethod
    def palm_center_x(hand):
        return (
            hand[0].x
            + hand[5].x
            + hand[9].x
            + hand[13].x
            + hand[17].x
        ) / 5

    # =====================================================
    # VOLUME
    # =====================================================

    def calculate_volume(self, hand_x):
        normalized_x = (
            (hand_x - self.VOLUME_LEFT_X)
            / (
                self.VOLUME_RIGHT_X
                - self.VOLUME_LEFT_X
            )
        )

        normalized_x = self.clamp(
            normalized_x,
            0.0,
            1.0
        )

        target_volume = normalized_x * 100

        if self.smoothed_volume is None:
            self.smoothed_volume = target_volume

        else:
            self.smoothed_volume = (
                0.90 * self.smoothed_volume
                + 0.10 * target_volume
            )

        stepped_volume = round(
            self.smoothed_volume
            / self.VOLUME_STEP
        ) * self.VOLUME_STEP

        return int(
            self.clamp(
                stepped_volume,
                0,
                100
            )
        )

    def send_volume(self, volume):
        now = time.time()

        changed_enough = (
            abs(volume - self.last_volume_sent)
            >= self.VOLUME_STEP
        )

        enough_time = (
            now - self.last_volume_send_time
            >= self.VOLUME_SEND_INTERVAL
        )

        if changed_enough and enough_time:
            spotify.set_volume(volume)

            self.last_volume_sent = volume
            self.last_volume_send_time = now

    @staticmethod
    def draw_volume_bar(frame, volume):
        height, width, _ = frame.shape

        left = 60
        right = width - 60

        top = height - 55
        bottom = height - 30

        cv2.rectangle(
            frame,
            (left, top),
            (right, bottom),
            (255, 255, 255),
            2
        )

        filled = int(
            (right - left)
            * volume
            / 100
        )

        cv2.rectangle(
            frame,
            (left, top),
            (left + filled, bottom),
            (0, 255, 0),
            -1
        )

        cv2.putText(
            frame,
            f"{volume}%",
            (right - 55, top - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )

    # =====================================================
    # GESTURE COUNTERS
    # =====================================================

    def reset_gesture_counters(self):
        self.fist_frames = 0
        self.thumbs_up_frames = 0
        self.thumbs_down_frames = 0
        self.two_finger_frames = 0
        self.three_finger_frames = 0

    def reset_other_counters(self, active):
        if active != "fist":
            self.fist_frames = 0

        if active != "thumbs_up":
            self.thumbs_up_frames = 0

        if active != "thumbs_down":
            self.thumbs_down_frames = 0

        if active != "two_fingers":
            self.two_finger_frames = 0

        if active != "three_fingers":
            self.three_finger_frames = 0

    # =====================================================
    # CAMERA LOOP
    # =====================================================

    def update_frame(self):
        if not self.running:
            return

        success, frame = self.cap.read()

        if success:
            frame = cv2.flip(
                frame,
                1
            )

            rgb_frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame
            )

            timestamp_ms = int(
                self.frame_index
                * (1000 / 30)
            )

            result = self.landmarker.detect_for_video(
                mp_image,
                timestamp_ms
            )

            self.frame_index += 1

            gesture_text = "SHOW YOUR HAND"

            if result.hand_landmarks:
                hand = result.hand_landmarks[0]

                height, width, _ = frame.shape
                now = time.time()

                for landmark in hand:
                    x = int(landmark.x * width)
                    y = int(landmark.y * height)

                    cv2.circle(
                        frame,
                        (x, y),
                        3,
                        (0, 255, 0),
                        -1
                    )

                is_two_fingers = self.detect_two_fingers(hand)
                is_three_fingers = self.detect_three_fingers(hand)
                is_thumbs_up = self.detect_thumbs_up(hand)
                is_thumbs_down = self.detect_thumbs_down(hand)

                is_fist = (
                    self.detect_fist(hand)
                    and not is_thumbs_up
                    and not is_thumbs_down
                    and not is_two_fingers
                    and not is_three_fingers
                )

                pinch_distance = self.get_pinch_distance(hand)

                any_command = (
                    is_two_fingers
                    or is_three_fingers
                    or is_thumbs_up
                    or is_thumbs_down
                    or is_fist
                )

                if not any_command:
                    self.action_locked = False

                if is_two_fingers:
                    self.two_finger_frames += 1
                    self.reset_other_counters("two_fingers")

                    gesture_text = "2 FINGERS - LOCK VOLUME"

                    if (
                        self.two_finger_frames
                        >= self.LOCK_FRAMES_NEEDED
                        and not self.action_locked
                        and now - self.last_action_time
                        > self.ACTION_COOLDOWN
                    ):
                        self.volume_locked = True
                        self.volume_mode = False
                        self.smoothed_volume = None
                        self.action_locked = True
                        self.last_action_time = now

                elif is_three_fingers:
                    self.three_finger_frames += 1
                    self.reset_other_counters("three_fingers")

                    gesture_text = "3 FINGERS - UNLOCK VOLUME"

                    if (
                        self.three_finger_frames
                        >= self.LOCK_FRAMES_NEEDED
                        and not self.action_locked
                        and now - self.last_action_time
                        > self.ACTION_COOLDOWN
                    ):
                        self.volume_locked = False
                        self.action_locked = True
                        self.last_action_time = now

                elif is_thumbs_up:
                    self.thumbs_up_frames += 1
                    self.reset_other_counters("thumbs_up")

                    gesture_text = "THUMBS UP - NEXT SONG"

                    if (
                        self.thumbs_up_frames
                        >= self.THUMB_FRAMES_NEEDED
                        and not self.action_locked
                        and now - self.last_action_time
                        > self.ACTION_COOLDOWN
                    ):
                        spotify.next_track()

                        self.action_locked = True
                        self.last_action_time = now

                        self.container.after(
                            700,
                            self.refresh_spotify_sidebar_once
                        )

                elif is_thumbs_down:
                    self.thumbs_down_frames += 1
                    self.reset_other_counters("thumbs_down")

                    gesture_text = "THUMBS DOWN - PREVIOUS SONG"

                    if (
                        self.thumbs_down_frames
                        >= self.THUMB_FRAMES_NEEDED
                        and not self.action_locked
                        and now - self.last_action_time
                        > self.ACTION_COOLDOWN
                    ):
                        spotify.previous_track()

                        self.action_locked = True
                        self.last_action_time = now

                        self.container.after(
                            700,
                            self.refresh_spotify_sidebar_once
                        )

                elif is_fist:
                    self.fist_frames += 1
                    self.reset_other_counters("fist")

                    gesture_text = "FIST - PLAY / PAUSE"

                    if (
                        self.fist_frames
                        >= self.FIST_FRAMES_NEEDED
                        and not self.action_locked
                        and now - self.last_action_time
                        > self.ACTION_COOLDOWN
                    ):
                        if self.is_paused:
                            spotify.play()
                            self.is_paused = False

                        else:
                            spotify.pause()
                            self.is_paused = True

                        self.action_locked = True
                        self.last_action_time = now

                        self.container.after(
                            500,
                            self.refresh_spotify_sidebar_once
                        )

                else:
                    self.reset_gesture_counters()

                    if self.volume_locked:
                        self.volume_mode = False
                        self.pinch_frames = 0

                        gesture_text = (
                            "VOLUME LOCKED - SHOW 3 FINGERS"
                        )

                    else:
                        if not self.volume_mode:
                            if (
                                pinch_distance
                                < self.PINCH_START_THRESHOLD
                            ):
                                self.pinch_frames += 1
                                gesture_text = "HOLD PINCH..."

                            else:
                                self.pinch_frames = 0
                                gesture_text = "READY"

                            if (
                                self.pinch_frames
                                >= self.PINCH_START_FRAMES
                            ):
                                self.volume_mode = True
                                self.smoothed_volume = None
                                self.pinch_frames = 0

                        if self.volume_mode:
                            gesture_text = (
                                "VOLUME - MOVE LEFT / RIGHT"
                            )

                            hand_x = self.palm_center_x(hand)

                            self.current_volume = (
                                self.calculate_volume(hand_x)
                            )

                            self.send_volume(
                                self.current_volume
                            )

                            if (
                                pinch_distance
                                > self.PINCH_RELEASE_THRESHOLD
                            ):
                                self.volume_mode = False
                                self.smoothed_volume = None

                spotify_status = (
                    "PAUSED"
                    if self.is_paused
                    else "PLAYING"
                )

                volume_status = (
                    "LOCKED"
                    if self.volume_locked
                    else "UNLOCKED"
                )

                cv2.putText(
                    frame,
                    f"SPOTIFY: {spotify_status}",
                    (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.72,
                    (0, 255, 255),
                    2
                )

                cv2.putText(
                    frame,
                    f"VOLUME: {volume_status}",
                    (15, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.68,
                    (0, 255, 255),
                    2
                )

                cv2.putText(
                    frame,
                    gesture_text,
                    (15, 92),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.62,
                    (255, 255, 255),
                    2
                )

                if self.volume_mode:
                    self.draw_volume_bar(
                        frame,
                        self.current_volume
                    )

                self.gesture_status.configure(
                    text=f"✋  {gesture_text}",
                    text_color=ACCENT
                )

            else:
                self.reset_gesture_counters()

                self.pinch_frames = 0
                self.volume_mode = False
                self.action_locked = False
                self.smoothed_volume = None

                cv2.putText(
                    frame,
                    "NO HAND DETECTED",
                    (15, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (0, 0, 255),
                    2
                )

                self.gesture_status.configure(
                    text="✋  No hand detected",
                    text_color="#f87171"
                )

            rgb_display = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            image = Image.fromarray(
                rgb_display
            )

            ctk_image = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=(640, 480)
            )

            self.video_label.configure(
                image=ctk_image,
                text=""
            )

            self.video_label.image = ctk_image

        else:
            self.camera_status_label.configure(
                text="● Camera unavailable",
                text_color="#f87171"
            )

        if self.running:
            self.container.after(
                33,
                self.update_frame
            )

    # =====================================================
    # CLOSE SCREEN
    # =====================================================

    def stop(self):
        self.running = False

        try:
            if self.cap:
                self.cap.release()

        except Exception as error:
            print(f"Camera release error: {error}")

        try:
            if self.landmarker:
                self.landmarker.close()

        except Exception as error:
            print(f"MediaPipe close error: {error}")

        try:
            self.container.destroy()

        except Exception:
            pass

        self.on_back()