import customtkinter as ctk
import subprocess
from tkinter import filedialog, Canvas
from handwaft_screen import HandwaftScreen
from dj_screen import DJScreen

ctk.set_appearance_mode("dark")

ACCENT = "#22d3ee"
ACCENT_HOVER = "#0891b2"
ACCENT_DIM = "#0e2a30"
TEXT_DIM = "#8b95a3"
CARD_BG = "#141a24"
CARD_BORDER = "#242d3a"

def launch_handwaft():
    for widget in main_frame.winfo_children():
        widget.destroy()
    HandwaftScreen(main_frame, show_home)

def launch_dj_mode():
    file_path = filedialog.askopenfilename(
        title="Choose a song",
        filetypes=[("Audio files", "*.wav")]
    )
    if file_path:
        for widget in main_frame.winfo_children():
            widget.destroy()
        DJScreen(main_frame, show_home, file_path)

def launch_spotify_mode():
    subprocess.Popen(["py", "spotify_mode.py"])

def show_home():
    for widget in main_frame.winfo_children():
        widget.destroy()
    build_home_screen()

def show_gestures_guide():
    for widget in main_frame.winfo_children():
        widget.destroy()
    build_gestures_screen()

def draw_gradient_bg(canvas, width, height, color_top, color_bottom):
    steps = 100
    r1, g1, b1 = canvas.winfo_rgb(color_top)
    r2, g2, b2 = canvas.winfo_rgb(color_bottom)
    for i in range(steps):
        ratio = i / steps
        r = int(r1 + (r2 - r1) * ratio) >> 8
        g = int(g1 + (g2 - g1) * ratio) >> 8
        b = int(b1 + (b2 - b1) * ratio) >> 8
        color = f"#{r:02x}{g:02x}{b:02x}"
        y0 = int(height * ratio)
        y1 = int(height * (ratio + 1 / steps))
        canvas.create_rectangle(0, y0, width, y1, fill=color, outline="")

def build_home_screen():
    canvas = Canvas(main_frame, width=700, height=800, highlightthickness=0, bd=0)
    canvas.place(x=0, y=0)
    draw_gradient_bg(canvas, 700, 800, "#0a0e16", "#0d1420")

    content = ctk.CTkFrame(main_frame, fg_color="transparent")
    content.place(relx=0.5, rely=0, anchor="n", y=45)

    badge = ctk.CTkLabel(content, text="●  Live gesture control",
                          font=("Segoe UI", 12, "bold"), text_color=ACCENT,
                          fg_color=ACCENT_DIM, corner_radius=20)
    badge.pack(ipadx=14, ipady=6, pady=(0, 28))

    title = ctk.CTkLabel(content, text="Handwaft", font=("Segoe UI", 52, "bold"),
                          text_color="white")
    title.pack()

    tagline = ctk.CTkLabel(content, text="Make music with your hands.",
                            font=("Segoe UI", 17), text_color=ACCENT)
    tagline.pack(pady=(6, 14))

    subtitle = ctk.CTkLabel(content,
                             text="Turn gestures into sound — build music from scratch,\nremix your own tracks, or control Spotify hands-free.",
                             font=("Segoe UI", 13), text_color=TEXT_DIM, justify="center")
    subtitle.pack(pady=(0, 36))

    hero_button = ctk.CTkButton(content, text="🎵   Start Handwaft",
                                  font=("Segoe UI", 18, "bold"), height=64, width=440,
                                  corner_radius=32,
                                  fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                  text_color="#04141a",
                                  command=launch_handwaft)
    hero_button.pack(pady=(0, 14))

    hero_note = ctk.CTkLabel(content, text="No files needed — just show your hand",
                              font=("Segoe UI", 11), text_color=TEXT_DIM)
    hero_note.pack(pady=(0, 34))

    cards_frame = ctk.CTkFrame(content, fg_color="transparent")
    cards_frame.pack()

    dj_card = ctk.CTkFrame(cards_frame, fg_color=CARD_BG, corner_radius=18,
                             border_width=1, border_color=CARD_BORDER, width=210, height=170)
    dj_card.grid(row=0, column=0, padx=8)
    dj_card.pack_propagate(False)
    dj_card.grid_propagate(False)

    ctk.CTkLabel(dj_card, text="🎧", font=("Segoe UI", 26)).pack(pady=(18, 4))
    ctk.CTkLabel(dj_card, text="DJ Mode", font=("Segoe UI", 15, "bold")).pack()
    ctk.CTkLabel(dj_card, text="Remix your own songs", font=("Segoe UI", 11),
                 text_color=TEXT_DIM).pack(pady=(2, 10))
    ctk.CTkButton(dj_card, text="Open", font=("Segoe UI", 12, "bold"), height=32, width=90,
                   corner_radius=16, fg_color="transparent", border_width=1,
                   border_color=ACCENT, text_color=ACCENT, hover_color=ACCENT_DIM,
                   command=launch_dj_mode).pack()

    spotify_card = ctk.CTkFrame(cards_frame, fg_color=CARD_BG, corner_radius=18,
                                  border_width=1, border_color=CARD_BORDER, width=210, height=170)
    spotify_card.grid(row=0, column=1, padx=8)
    spotify_card.pack_propagate(False)
    spotify_card.grid_propagate(False)

    ctk.CTkLabel(spotify_card, text="🟢", font=("Segoe UI", 26)).pack(pady=(18, 4))
    ctk.CTkLabel(spotify_card, text="Spotify Mode", font=("Segoe UI", 15, "bold")).pack()
    ctk.CTkLabel(spotify_card, text="Control your playback", font=("Segoe UI", 11),
                 text_color=TEXT_DIM).pack(pady=(2, 10))
    ctk.CTkButton(spotify_card, text="Open", font=("Segoe UI", 12, "bold"), height=32, width=90,
                   corner_radius=16, fg_color="transparent", border_width=1,
                   border_color=ACCENT, text_color=ACCENT, hover_color=ACCENT_DIM,
                   command=launch_spotify_mode).pack()

    gestures_link = ctk.CTkButton(content, text="✋  View gesture guide",
                                    font=("Segoe UI", 12), height=36,
                                    corner_radius=18, fg_color="transparent",
                                    hover_color=CARD_BG, text_color=TEXT_DIM,
                                    command=show_gestures_guide)
    gestures_link.pack(pady=(30, 0))

def build_gestures_screen():
    canvas = Canvas(main_frame, width=700, height=800, highlightthickness=0, bd=0)
    canvas.place(x=0, y=0)
    draw_gradient_bg(canvas, 700, 800, "#0a0e16", "#0d1420")

    content = ctk.CTkFrame(main_frame, fg_color="transparent")
    content.place(relx=0.5, rely=0, anchor="n", y=30)

    back_button = ctk.CTkButton(content, text="← Back", font=("Segoe UI", 13, "bold"),
                                  width=90, height=36, corner_radius=18,
                                  fg_color=CARD_BG, hover_color=CARD_BORDER,
                                  text_color="white",
                                  command=show_home)
    back_button.pack(anchor="w", pady=(0, 20))

    title = ctk.CTkLabel(content, text="Gesture Guide", font=("Segoe UI", 30, "bold"))
    title.pack(anchor="w", pady=(0, 4))

    sub = ctk.CTkLabel(content, text="Every control, across every mode.",
                        font=("Segoe UI", 13), text_color=TEXT_DIM)
    sub.pack(anchor="w", pady=(0, 20))

    scroll_frame = ctk.CTkScrollableFrame(content, width=480, height=440,
                                            fg_color="transparent")
    scroll_frame.pack()

    def add_section(icon, name, gestures):
        header = ctk.CTkLabel(scroll_frame, text=f"{icon}  {name}",
                                font=("Segoe UI", 16, "bold"), text_color=ACCENT)
        header.pack(anchor="w", pady=(18, 10))
        for gesture, action in gestures:
            row = ctk.CTkFrame(scroll_frame, fg_color=CARD_BG, corner_radius=12,
                                 border_width=1, border_color=CARD_BORDER)
            row.pack(fill="x", pady=4)
            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=16, pady=12)
            ctk.CTkLabel(inner, text=gesture, font=("Segoe UI", 13, "bold"),
                         text_color="white", anchor="w").pack(side="left")
            ctk.CTkLabel(inner, text=action, font=("Segoe UI", 13),
                         text_color=ACCENT, anchor="e").pack(side="right")

    add_section("🎧", "DJ Mode", [
        ("Move left / right", "Speed"),
        ("Move up / down", "Volume"),
        ("Make a fist", "Bass boost"),
    ])
    add_section("🟢", "Spotify Mode", [
        ("Fist", "Play / Pause"),
        ("Thumbs up", "Next song"),
        ("Thumbs down", "Previous song"),
        ("2 fingers up", "Lock volume"),
        ("3 fingers up", "Unlock volume"),
        ("Pinch + move", "Adjust volume"),
    ])
    add_section("🎵", "Handwaft Mode", [
        ("Wrist tilt", "Pitch"),
        ("Hand height", "Volume"),
        ("Fist ↔ open", "Brightness"),
        ("Finger spread", "Chord density"),
    ])

root = ctk.CTk()
root.title("Handwaft")
root.geometry("700x800")

main_frame = ctk.CTkFrame(root, fg_color="#0a0e16")
main_frame.pack(fill="both", expand=True)

build_home_screen()

root.mainloop() 
