import sounddevice as sd
import numpy as np

SAMPLE_RATE = 44100

current_frequency = 440
current_volume = 0.3  # 0.0 = silent, 1.0 = max loud

def audio_callback(outdata, frames, time, status):
    t = (np.arange(frames) + audio_callback.phase) / SAMPLE_RATE
    wave = current_volume * np.sin(2 * np.pi * current_frequency * t)
    outdata[:, 0] = wave
    audio_callback.phase += frames

audio_callback.phase = 0

with sd.OutputStream(channels=1, samplerate=SAMPLE_RATE, callback=audio_callback):
    print("Playing. Type 'f 300' to change frequency, 'v 0.5' to change volume, 'q' to quit.")
    while True:
        user_input = input("> ")
        if user_input == 'q':
            break
        parts = user_input.split()
        if len(parts) != 2:
            print("Type like: f 300  or  v 0.5")
            continue
        command, value = parts
        if command == 'f':
            current_frequency = float(value)
        elif command == 'v':
            current_volume = float(value)
        else:
            print("Unknown command. Use 'f' for frequency or 'v' for volume.")