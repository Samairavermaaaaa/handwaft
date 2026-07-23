import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import time
import math

import spotify_control as spotify


# =========================================================
# MEDIAPIPE SETUP
# =========================================================

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

landmarker = HandLandmarker.create_from_options(options)


# =========================================================
# CAMERA SETUP
# =========================================================

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("Could not open webcam.")
    raise SystemExit


# =========================================================
# SETTINGS
# =========================================================

frame_index = 0

# Change this to True if Spotify is paused when program starts.
is_paused = False

# Volume starts unlocked.
volume_locked = False
volume_mode = False

# Faster gesture recognition
FIST_FRAMES_NEEDED = 3
THUMB_FRAMES_NEEDED = 3
LOCK_FRAMES_NEEDED = 4

ACTION_COOLDOWN = 0.55
last_action_time = 0

# Gesture counters
fist_frames = 0
thumbs_up_frames = 0
thumbs_down_frames = 0
two_finger_frames = 0
three_finger_frames = 0
pinch_frames = 0

# Prevent repeated commands while holding the gesture.
action_locked = False

# Volume settings
PINCH_START_THRESHOLD = 0.30
PINCH_RELEASE_THRESHOLD = 0.48
PINCH_START_FRAMES = 4

VOLUME_LEFT_X = 0.18
VOLUME_RIGHT_X = 0.82

VOLUME_STEP = 5
VOLUME_SEND_INTERVAL = 0.18

smoothed_volume = None
last_volume_sent = -1
last_volume_send_time = 0


# =========================================================
# BASIC HELPERS
# =========================================================

def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def point_distance(point_1, point_2):
    return math.sqrt(
        ((point_1.x - point_2.x) ** 2)
        + ((point_1.y - point_2.y) ** 2)
    )


def palm_size(hand):
    """
    Wrist to middle-finger base distance.
    Used to normalize gesture measurements.
    """
    size = point_distance(hand[0], hand[9])
    return max(size, 0.01)


def normalized_distance(hand, point_1, point_2):
    return (
        point_distance(hand[point_1], hand[point_2])
        / palm_size(hand)
    )


# =========================================================
# FINGER DETECTION
# =========================================================

def finger_extended(hand, tip, pip, mcp):
    """
    Finger is extended when its tip is clearly above
    its PIP joint and its PIP is near/above its MCP.
    """
    return (
        hand[tip].y < hand[pip].y - 0.01
        and hand[pip].y < hand[mcp].y + 0.04
    )


def index_extended(hand):
    return finger_extended(hand, 8, 6, 5)


def middle_extended(hand):
    return finger_extended(hand, 12, 10, 9)


def ring_extended(hand):
    return finger_extended(hand, 16, 14, 13)


def pinky_extended(hand):
    return finger_extended(hand, 20, 18, 17)


def index_curled(hand):
    return not index_extended(hand)


def middle_curled(hand):
    return not middle_extended(hand)


def ring_curled(hand):
    return not ring_extended(hand)


def pinky_curled(hand):
    return not pinky_extended(hand)


def closed_finger_count(hand):
    return sum([
        index_curled(hand),
        middle_curled(hand),
        ring_curled(hand),
        pinky_curled(hand)
    ])


# =========================================================
# GESTURE DETECTION
# =========================================================

def detect_thumbs_up(hand):
    """
    Thumb points upward and at least three fingers are closed.
    """
    thumb_points_up = (
        hand[4].y < hand[3].y
        and hand[4].y < hand[2].y
        and hand[4].y < hand[5].y
    )

    thumb_separated = (
        normalized_distance(hand, 4, 9) > 0.62
    )

    return (
        thumb_points_up
        and thumb_separated
        and closed_finger_count(hand) >= 3
    )


def detect_thumbs_down(hand):
    """
    Thumb points downward and at least three fingers are closed.
    """
    thumb_points_down = (
        hand[4].y > hand[3].y
        and hand[4].y > hand[2].y
        and hand[4].y > hand[5].y
    )

    thumb_separated = (
        normalized_distance(hand, 4, 9) > 0.62
    )

    return (
        thumb_points_down
        and thumb_separated
        and closed_finger_count(hand) >= 3
    )


def detect_fist(hand):
    """
    Fist detection is intentionally lenient.

    Three or four curled fingers are enough,
    but thumbs-up/down are checked before fist in the main loop.
    """
    return closed_finger_count(hand) >= 3


def detect_two_fingers(hand):
    """
    Index and middle up.
    Ring and pinky down.
    """
    return (
        index_extended(hand)
        and middle_extended(hand)
        and ring_curled(hand)
        and pinky_curled(hand)
    )


def detect_three_fingers(hand):
    """
    Index, middle and ring up.
    Pinky down.
    """
    return (
        index_extended(hand)
        and middle_extended(hand)
        and ring_extended(hand)
        and pinky_curled(hand)
    )


def get_pinch_distance(hand):
    """
    Distance between thumb tip and index fingertip.
    """
    return normalized_distance(hand, 4, 8)


def palm_center_x(hand):
    """
    Average horizontal position of palm landmarks.
    """
    return (
        hand[0].x
        + hand[5].x
        + hand[9].x
        + hand[13].x
        + hand[17].x
    ) / 5


# =========================================================
# VOLUME CONTROL
# =========================================================

def calculate_volume(hand_x):
    global smoothed_volume

    normalized_x = (
        (hand_x - VOLUME_LEFT_X)
        / (VOLUME_RIGHT_X - VOLUME_LEFT_X)
    )

    normalized_x = clamp(normalized_x, 0.0, 1.0)
    target_volume = normalized_x * 100

    if smoothed_volume is None:
        smoothed_volume = target_volume
    else:
        # Strong smoothing
        smoothed_volume = (
            0.90 * smoothed_volume
            + 0.10 * target_volume
        )

    stepped_volume = round(
        smoothed_volume / VOLUME_STEP
    ) * VOLUME_STEP

    return int(clamp(stepped_volume, 0, 100))


def send_volume(volume):
    global last_volume_sent
    global last_volume_send_time

    now = time.time()

    changed_enough = (
        abs(volume - last_volume_sent) >= VOLUME_STEP
    )

    enough_time_passed = (
        now - last_volume_send_time
        >= VOLUME_SEND_INTERVAL
    )

    if changed_enough and enough_time_passed:
        spotify.set_volume(volume)

        last_volume_sent = volume
        last_volume_send_time = now


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

    filled_width = int(
        (right - left) * volume / 100
    )

    cv2.rectangle(
        frame,
        (left, top),
        (left + filled_width, bottom),
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


# =========================================================
# RESET FUNCTIONS
# =========================================================

def reset_gesture_counters():
    global fist_frames
    global thumbs_up_frames
    global thumbs_down_frames
    global two_finger_frames
    global three_finger_frames

    fist_frames = 0
    thumbs_up_frames = 0
    thumbs_down_frames = 0
    two_finger_frames = 0
    three_finger_frames = 0


def reset_other_counters(active_gesture):
    global fist_frames
    global thumbs_up_frames
    global thumbs_down_frames
    global two_finger_frames
    global three_finger_frames

    if active_gesture != "fist":
        fist_frames = 0

    if active_gesture != "thumbs_up":
        thumbs_up_frames = 0

    if active_gesture != "thumbs_down":
        thumbs_down_frames = 0

    if active_gesture != "two_fingers":
        two_finger_frames = 0

    if active_gesture != "three_fingers":
        three_finger_frames = 0


# =========================================================
# START INFORMATION
# =========================================================

print("Spotify gesture control started.")
print("FIST = Play/Pause")
print("THUMBS UP = Next song")
print("THUMBS DOWN = Previous song")
print("2 FINGERS = Lock volume")
print("3 FINGERS = Unlock volume")
print("PINCH + MOVE LEFT/RIGHT = Change volume")
print("Press Q to quit.")


# =========================================================
# MAIN LOOP
# =========================================================

while True:
    success, frame = cap.read()

    if not success:
        continue

    # Mirror camera view.
    frame = cv2.flip(frame, 1)

    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb_frame
    )

    timestamp_ms = int(
        frame_index * (1000 / 30)
    )

    result = landmarker.detect_for_video(
        mp_image,
        timestamp_ms
    )

    frame_index += 1

    gesture_text = "SHOW YOUR HAND"
    current_volume = max(last_volume_sent, 0)

    if result.hand_landmarks:
        hand = result.hand_landmarks[0]

        height, width, _ = frame.shape
        now = time.time()

        # Draw hand landmarks
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

        # Detect all gestures
        is_two_fingers = detect_two_fingers(hand)
        is_three_fingers = detect_three_fingers(hand)
        is_thumbs_up = detect_thumbs_up(hand)
        is_thumbs_down = detect_thumbs_down(hand)

        # Fist must be checked after thumbs gestures.
        is_fist = (
            detect_fist(hand)
            and not is_thumbs_up
            and not is_thumbs_down
            and not is_two_fingers
            and not is_three_fingers
        )

        pinch_distance = get_pinch_distance(hand)

        any_command_gesture = (
            is_two_fingers
            or is_three_fingers
            or is_thumbs_up
            or is_thumbs_down
            or is_fist
        )

        # Unlock gesture action only after returning to neutral.
        if not any_command_gesture:
            action_locked = False

        # =================================================
        # TWO FINGERS: LOCK VOLUME
        # =================================================

        if is_two_fingers:
            two_finger_frames += 1
            reset_other_counters("two_fingers")

            gesture_text = "2 FINGERS - LOCK VOLUME"

            if (
                two_finger_frames >= LOCK_FRAMES_NEEDED
                and not action_locked
                and now - last_action_time > ACTION_COOLDOWN
            ):
                volume_locked = True
                volume_mode = False
                smoothed_volume = None

                print("Volume locked")

                action_locked = True
                last_action_time = now

        # =================================================
        # THREE FINGERS: UNLOCK VOLUME
        # =================================================

        elif is_three_fingers:
            three_finger_frames += 1
            reset_other_counters("three_fingers")

            gesture_text = "3 FINGERS - UNLOCK VOLUME"

            if (
                three_finger_frames >= LOCK_FRAMES_NEEDED
                and not action_locked
                and now - last_action_time > ACTION_COOLDOWN
            ):
                volume_locked = False

                print("Volume unlocked")

                action_locked = True
                last_action_time = now

        # =================================================
        # THUMBS UP: NEXT SONG
        # =================================================

        elif is_thumbs_up:
            thumbs_up_frames += 1
            reset_other_counters("thumbs_up")

            gesture_text = "THUMBS UP - NEXT SONG"

            if (
                thumbs_up_frames >= THUMB_FRAMES_NEEDED
                and not action_locked
                and now - last_action_time > ACTION_COOLDOWN
            ):
                spotify.next_track()

                print("Next song")

                action_locked = True
                last_action_time = now

        # =================================================
        # THUMBS DOWN: PREVIOUS SONG
        # =================================================

        elif is_thumbs_down:
            thumbs_down_frames += 1
            reset_other_counters("thumbs_down")

            gesture_text = "THUMBS DOWN - PREVIOUS SONG"

            if (
                thumbs_down_frames >= THUMB_FRAMES_NEEDED
                and not action_locked
                and now - last_action_time > ACTION_COOLDOWN
            ):
                spotify.previous_track()

                print("Previous song")

                action_locked = True
                last_action_time = now

        # =================================================
        # FIST: PLAY / PAUSE
        # =================================================

        elif is_fist:
            fist_frames += 1
            reset_other_counters("fist")

            gesture_text = "FIST - PLAY / PAUSE"

            if (
                fist_frames >= FIST_FRAMES_NEEDED
                and not action_locked
                and now - last_action_time > ACTION_COOLDOWN
            ):
                if is_paused:
                    spotify.play()
                    is_paused = False
                    print("Playing")

                else:
                    spotify.pause()
                    is_paused = True
                    print("Paused")

                action_locked = True
                last_action_time = now

        # =================================================
        # VOLUME MODE
        # =================================================

        else:
            reset_gesture_counters()

            if volume_locked:
                volume_mode = False
                pinch_frames = 0

                gesture_text = "VOLUME LOCKED - SHOW 3 FINGERS"

            else:
                if not volume_mode:
                    if pinch_distance < PINCH_START_THRESHOLD:
                        pinch_frames += 1
                        gesture_text = "HOLD PINCH..."

                    else:
                        pinch_frames = 0
                        gesture_text = "READY"

                    if pinch_frames >= PINCH_START_FRAMES:
                        volume_mode = True
                        smoothed_volume = None
                        pinch_frames = 0

                        print("Volume mode active")

                if volume_mode:
                    gesture_text = "VOLUME - MOVE LEFT / RIGHT"

                    hand_x = palm_center_x(hand)
                    current_volume = calculate_volume(hand_x)

                    send_volume(current_volume)

                    if pinch_distance > PINCH_RELEASE_THRESHOLD:
                        volume_mode = False
                        smoothed_volume = None

                        print(
                            f"Volume set to {current_volume}%"
                        )

        # =================================================
        # SCREEN UI
        # =================================================

        spotify_status = (
            "PAUSED"
            if is_paused
            else "PLAYING"
        )

        volume_status = (
            "LOCKED"
            if volume_locked
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

        if volume_mode:
            draw_volume_bar(
                frame,
                current_volume
            )

    else:
        reset_gesture_counters()

        pinch_frames = 0
        volume_mode = False
        action_locked = False
        smoothed_volume = None

        cv2.putText(
            frame,
            "NO HAND DETECTED",
            (15, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 0, 255),
            2
        )

    cv2.imshow(
        "Handwaft Spotify Control",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


cap.release()
landmarker.close()
cv2.destroyAllWindows()