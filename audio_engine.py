import numpy as np
import sounddevice as sd

SAMPLE_RATE = 44100

# --- Musical scale setup ---
# C major pentatonic scale, spanning 2 octaves: C, D, E, G, A (no F or B - avoids "wrong note" feel)
NOTE_NAMES = ["C4", "D4", "E4", "G4", "A4", "C5", "D5", "E5", "G5", "A5"]
NOTE_FREQS = [261.63, 293.66, 329.63, 392.00, 440.00,
              523.25, 587.33, 659.25, 783.99, 880.00]


def _quantize_to_scale(raw_freq):
    """Snaps a raw frequency to the nearest note in NOTE_FREQS."""
    closest_index = min(
        range(len(NOTE_FREQS)),
        key=lambda i: abs(NOTE_FREQS[i] - raw_freq)
    )
    return NOTE_FREQS[closest_index]


target_freq = NOTE_FREQS[0]
target_volume = 0.0
target_brightness = 0.0
target_vibrato_depth = 0.0

current_freq = NOTE_FREQS[0]
current_volume = 0.0
current_brightness = 0.0
current_vibrato_depth = 0.0

phase = 0.0
vibrato_phase = 0.0
stream = None

GLIDE_SPEED = 0.08  # slightly snappier now, since notes should feel more "landed"

filter_state = 0.0
FILTER_AMOUNT = 0.15


def _sawtooth(freq_array, t):
    phase_pos = (freq_array * t) % 1.0
    return 2 * phase_pos - 1


def _apply_warmth_filter(wave):
    global filter_state
    filtered = np.empty_like(wave)
    for i in range(len(wave)):
        filter_state += (wave[i] - filter_state) * FILTER_AMOUNT
        filtered[i] = filter_state
    return filtered


def _audio_callback(outdata, frames, time, status):
    global phase, vibrato_phase
    global current_freq, current_volume, current_brightness, current_vibrato_depth

    current_freq += (target_freq - current_freq) * GLIDE_SPEED
    current_volume += (target_volume - current_volume) * GLIDE_SPEED
    current_brightness += (target_brightness - current_brightness) * GLIDE_SPEED
    current_vibrato_depth += (target_vibrato_depth - current_vibrato_depth) * GLIDE_SPEED

    t = (np.arange(frames) + phase) / SAMPLE_RATE

    vibrato = np.sin(2 * np.pi * 5 * (np.arange(frames) + vibrato_phase) / SAMPLE_RATE)
    wobble_freq = current_freq * (1 + 0.02 * current_vibrato_depth * vibrato)

    sine_part = np.sin(2 * np.pi * wobble_freq * t)
    saw_part = _sawtooth(wobble_freq, t)
    wave = (1 - current_brightness) * sine_part + current_brightness * saw_part
    wave += current_brightness * 0.3 * np.sin(2 * np.pi * wobble_freq * 2 * t)
    wave = wave / (1 + current_brightness * 0.5)

    wave = _apply_warmth_filter(wave)

    outdata[:, 0] = wave * current_volume

    phase += frames
    vibrato_phase += frames


def start_audio():
    global stream
    stream = sd.OutputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        callback=_audio_callback
    )
    stream.start()


def stop_audio():
    if stream is not None:
        stream.stop()


def send_to_audio(params):
    global target_freq, target_volume, target_brightness, target_vibrato_depth

    target_volume = params["curl"]

    # Map tilt (-1 to 1) across the note range, then snap to nearest scale note
    raw_freq = 261.63 + (params["tilt"] + 1) * 300  # rough range covering the scale
    target_freq = _quantize_to_scale(raw_freq)

    target_brightness = min(params["spread"] * 5, 1.0)
    target_vibrato_depth = params["height"]


def silence():
    global target_volume
    target_volume = 0.0