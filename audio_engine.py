import sounddevice as sd
import numpy as np

SAMPLE_RATE = 44100

current_frequency = 440
current_volume = 0.3
current_brightness = 0.0  # 0.0 = pure tone, 1.0 = very bright/buzzy

def audio_callback(outdata, frames, time, status):
    t = (np.arange(frames) + audio_callback.phase) / SAMPLE_RATE
    
    # Base tone
    wave = np.sin(2 * np.pi * current_frequency * t)
    
    # Add harmonics, scaled down by brightness
    wave += current_brightness * 0.5 * np.sin(2 * np.pi * current_frequency * 2 * t)
    wave += current_brightness * 0.3 * np.sin(2 * np.pi * current_frequency * 3 * t)
    wave += current_brightness * 0.2 * np.sin(2 * np.pi * current_frequency * 4 * t)
    
    # Normalize so it doesn't get too loud with harmonics added, then apply volume
    wave = wave / (1 + current_brightness)
    outdata[:, 0] = current_volume * wave
    
    audio_callback.phase += frames

audio_callback.phase = 0

with sd.OutputStream(channels=1, samplerate=SAMPLE_RATE, callback=audio_callback):
    print("Playing. Commands: f <freq>, v <volume>, b <brightness 0-1>, q to quit.")
    while True:
        user_input = input("> ")
        if user_input == 'q':
            break
        parts = user_input.split()
        if len(parts) != 2:
            print("Type like: f 300  or  v 0.5  or  b 0.8")
            continue
        command, value = parts
        if command == 'f':
            current_frequency = float(value)
        elif command == 'v':
            current_volume = float(value)
        elif command == 'b':
            current_brightness = float(value)
        else:
            print("Unknown command.")