import sounddevice as sd
import numpy as np

SAMPLE_RATE = 44100
frequency = 440  

def audio_callback(outdata, frames, time, status):
    t = (np.arange(frames) + audio_callback.phase) / SAMPLE_RATE
    wave = 0.3 * np.sin(2 * np.pi * frequency * t)
    outdata[:, 0] = wave
    audio_callback.phase += frames

audio_callback.phase = 0

with sd.OutputStream(channels=1, samplerate=SAMPLE_RATE, callback=audio_callback):
    print("Playing... press Enter to stop.")
    input()