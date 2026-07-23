import customtkinter as ctk
from tkinter import filedialog, Canvas

from spotify_screen import SpotifyScreen
from handwaft_screen import HandwaftScreen
from dj_screen import DJScreen


# --------------------------------------------------
# APP SETTINGS
# --------------------------------------------------

ctk.set_appearance_mode("dark")

APP_WIDTH = 1100
APP_HEIGHT = 800

ACCENT = "#22d3ee"
ACCENT_HOVER = "#0891b2"
ACCENT_DIM = "#0e2a30"

TEXT_DIM = "#8b95a3"

CARD_BG = "#141a24"
CARD_BORDER = "#242d3a"

BACKGROUND_TOP = "#0a0e16"
BACKGROUND_BOTTOM = "#0d1420"


# --------------------------------------------------
# SCREEN NAVIGATION
# --------------------------------------------------

def clear_screen():
    """Remove every widget from the main screen."""
    for widget in main_frame.winfo_children():
        widget.destroy()


def launch_handwaft():
    clear_screen()
    HandwaftScreen(main_frame, show_home)


def launch_dj_mode():
    file_path = filedialog.askopenfilename(
        title="Choose a song",
        filetypes=[
            ("WAV Audio", "*.wav"),
            ("MP3 Audio", "*.mp3"),
            ("All audio files", "*.wav *.mp3")
        ]
    )

    if file_path:
        clear_screen()
        DJScreen(main_frame, show_home, file_path)


def launch_spotify_mode():
    clear_screen()

    # SpotifyScreen will contain:
    # 1. Camera/gesture area
    # 2. Now-playing sidebar
    SpotifyScreen(main_frame, show_home)


def show_home():
    clear_screen()
    build_home_screen()


def show_gestures_guide():
    clear_screen()
    build_gestures_screen()


# --------------------------------------------------
# BACKGROUND
# --------------------------------------------------

def draw_gradient_bg(
    canvas,
    width,
    height,
    color_top,
    color_bottom
):
    steps = 100

    red_1, green_1, blue_1 = canvas.winfo_rgb(color_top)
    red_2, green_2, blue_2 = canvas.winfo_rgb(color_bottom)

    for index in range(steps):
        ratio = index / steps

        red = int(red_1 + (red_2 - red_1) * ratio) >> 8
        green = int(green_1 + (green_2 - green_1) * ratio) >> 8
        blue = int(blue_1 + (blue_2 - blue_1) * ratio) >> 8

        color = f"#{red:02x}{green:02x}{blue:02x}"

        y_start = int(height * ratio)
        y_end = int(height * ((index + 1) / steps))

        canvas.create_rectangle(
            0,
            y_start,
            width,
            y_end,
            fill=color,
            outline=""
        )


def create_background():
    canvas = Canvas(
        main_frame,
        highlightthickness=0,
        bd=0,
        bg=BACKGROUND_TOP
    )

    canvas.place(
        x=0,
        y=0,
        relwidth=1,
        relheight=1
    )

    main_frame.update_idletasks()

    width = max(main_frame.winfo_width(), APP_WIDTH)
    height = max(main_frame.winfo_height(), APP_HEIGHT)

    draw_gradient_bg(
        canvas,
        width,
        height,
        BACKGROUND_TOP,
        BACKGROUND_BOTTOM
    )

    return canvas


# --------------------------------------------------
# HOME SCREEN
# --------------------------------------------------

def build_home_screen():
    create_background()

    content = ctk.CTkFrame(
        main_frame,
        fg_color="transparent"
    )

    content.place(
        relx=0.5,
        rely=0,
        anchor="n",
        y=35
    )

    badge = ctk.CTkLabel(
        content,
        text="●  Live gesture control",
        font=("Segoe UI", 12, "bold"),
        text_color=ACCENT,
        fg_color=ACCENT_DIM,
        corner_radius=20
    )

    badge.pack(
        ipadx=14,
        ipady=6,
        pady=(0, 22)
    )

    title = ctk.CTkLabel(
        content,
        text="Handwaft",
        font=("Segoe UI", 52, "bold"),
        text_color="white"
    )

    title.pack()

    tagline = ctk.CTkLabel(
        content,
        text="Make music with your hands.",
        font=("Segoe UI", 17),
        text_color=ACCENT
    )

    tagline.pack(pady=(6, 14))

    subtitle = ctk.CTkLabel(
        content,
        text=(
            "Turn gestures into sound — build music from scratch,\n"
            "remix your own tracks, or control Spotify hands-free."
        ),
        font=("Segoe UI", 13),
        text_color=TEXT_DIM,
        justify="center"
    )

    subtitle.pack(pady=(0, 30))

    hero_button = ctk.CTkButton(
        content,
        text="🎵   Start Handwaft",
        font=("Segoe UI", 18, "bold"),
        height=64,
        width=440,
        corner_radius=32,
        fg_color=ACCENT,
        hover_color=ACCENT_HOVER,
        text_color="#04141a",
        command=launch_handwaft
    )

    hero_button.pack(pady=(0, 14))

    hero_note = ctk.CTkLabel(
        content,
        text="No files needed — just show your hand",
        font=("Segoe UI", 11),
        text_color=TEXT_DIM
    )

    hero_note.pack(pady=(0, 28))

    cards_frame = ctk.CTkFrame(
        content,
        fg_color="transparent"
    )

    cards_frame.pack()

    create_mode_card(
        parent=cards_frame,
        column=0,
        icon="🎧",
        title="DJ Mode",
        description="Remix your own songs",
        command=launch_dj_mode
    )

    create_mode_card(
        parent=cards_frame,
        column=1,
        icon="🟢",
        title="Spotify Mode",
        description="Control your playback",
        command=launch_spotify_mode
    )

    gestures_link = ctk.CTkButton(
        content,
        text="✋  View gesture guide",
        font=("Segoe UI", 12),
        height=36,
        corner_radius=18,
        fg_color="transparent",
        hover_color=CARD_BG,
        text_color=TEXT_DIM,
        command=show_gestures_guide
    )

    gestures_link.pack(pady=(26, 0))


def create_mode_card(
    parent,
    column,
    icon,
    title,
    description,
    command
):
    card = ctk.CTkFrame(
        parent,
        fg_color=CARD_BG,
        corner_radius=18,
        border_width=1,
        border_color=CARD_BORDER,
        width=220,
        height=170
    )

    card.grid(
        row=0,
        column=column,
        padx=8
    )

    card.pack_propagate(False)
    card.grid_propagate(False)

    ctk.CTkLabel(
        card,
        text=icon,
        font=("Segoe UI Emoji", 26)
    ).pack(pady=(18, 4))

    ctk.CTkLabel(
        card,
        text=title,
        font=("Segoe UI", 15, "bold")
    ).pack()

    ctk.CTkLabel(
        card,
        text=description,
        font=("Segoe UI", 11),
        text_color=TEXT_DIM
    ).pack(pady=(2, 10))

    ctk.CTkButton(
        card,
        text="Open",
        font=("Segoe UI", 12, "bold"),
        height=32,
        width=90,
        corner_radius=16,
        fg_color="transparent",
        border_width=1,
        border_color=ACCENT,
        text_color=ACCENT,
        hover_color=ACCENT_DIM,
        command=command
    ).pack()


# --------------------------------------------------
# GESTURE GUIDE
# --------------------------------------------------

def build_gestures_screen():
    create_background()

    content = ctk.CTkFrame(
        main_frame,
        fg_color="transparent"
    )

    content.place(
        relx=0.5,
        rely=0,
        anchor="n",
        y=30
    )

    back_button = ctk.CTkButton(
        content,
        text="← Back",
        font=("Segoe UI", 13, "bold"),
        width=90,
        height=36,
        corner_radius=18,
        fg_color=CARD_BG,
        hover_color=CARD_BORDER,
        text_color="white",
        command=show_home
    )

    back_button.pack(
        anchor="w",
        pady=(0, 20)
    )

    title = ctk.CTkLabel(
        content,
        text="Gesture Guide",
        font=("Segoe UI", 30, "bold")
    )

    title.pack(
        anchor="w",
        pady=(0, 4)
    )

    subtitle = ctk.CTkLabel(
        content,
        text="Every control, across every mode.",
        font=("Segoe UI", 13),
        text_color=TEXT_DIM
    )

    subtitle.pack(
        anchor="w",
        pady=(0, 20)
    )

    scroll_frame = ctk.CTkScrollableFrame(
        content,
        width=520,
        height=520,
        fg_color="transparent"
    )

    scroll_frame.pack()

    add_gesture_section(
        scroll_frame,
        "🎧",
        "DJ Mode",
        [
            ("Move left / right", "Speed"),
            ("Move up / down", "Volume"),
            ("Make a fist", "Bass boost")
        ]
    )

    add_gesture_section(
        scroll_frame,
        "🟢",
        "Spotify Mode",
        [
            ("Fist", "Play / Pause"),
            ("Thumbs up", "Next song"),
            ("Thumbs down", "Previous song"),
            ("2 fingers up", "Lock volume"),
            ("3 fingers up", "Unlock volume"),
            ("Pinch + move", "Adjust volume")
        ]
    )

    add_gesture_section(
        scroll_frame,
        "🎵",
        "Handwaft Mode",
        [
            ("Wrist tilt", "Pitch"),
            ("Hand height", "Volume"),
            ("Fist ↔ open", "Brightness"),
            ("Finger spread", "Chord density")
        ]
    )


def add_gesture_section(
    parent,
    icon,
    section_name,
    gestures
):
    header = ctk.CTkLabel(
        parent,
        text=f"{icon}  {section_name}",
        font=("Segoe UI", 16, "bold"),
        text_color=ACCENT
    )

    header.pack(
        anchor="w",
        pady=(18, 10)
    )

    for gesture, action in gestures:
        row = ctk.CTkFrame(
            parent,
            fg_color=CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=CARD_BORDER
        )

        row.pack(
            fill="x",
            pady=4
        )

        inner = ctk.CTkFrame(
            row,
            fg_color="transparent"
        )

        inner.pack(
            fill="x",
            padx=16,
            pady=12
        )

        ctk.CTkLabel(
            inner,
            text=gesture,
            font=("Segoe UI", 13, "bold"),
            text_color="white",
            anchor="w"
        ).pack(side="left")

        ctk.CTkLabel(
            inner,
            text=action,
            font=("Segoe UI", 13),
            text_color=ACCENT,
            anchor="e"
        ).pack(side="right")


# --------------------------------------------------
# MAIN WINDOW
# --------------------------------------------------

root = ctk.CTk()

root.title("Handwaft")
root.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
root.minsize(900, 700)

# Open window in the centre of the screen
root.update_idletasks()

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

window_x = (screen_width - APP_WIDTH) // 2
window_y = (screen_height - APP_HEIGHT) // 2

root.geometry(
    f"{APP_WIDTH}x{APP_HEIGHT}+{window_x}+{window_y}"
)

main_frame = ctk.CTkFrame(
    root,
    fg_color=BACKGROUND_TOP,
    corner_radius=0
)

main_frame.pack(
    fill="both",
    expand=True
)

build_home_screen()

root.mainloop()