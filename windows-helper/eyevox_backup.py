
import os
import time
import threading
import subprocess

import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import speech_recognition as sr


# ============================================================
# SETTINGS
# ============================================================

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0

SCREEN_W, SCREEN_H = pyautogui.size()

BLINK_THRESHOLD = 0.015
CLICK_BLINK_TIME = 0.20
SCREENSHOT_BLINK_TIME = 1.0

SMOOTH_FACTOR = 0.18
VOICE_PHRASE_LIMIT = 6

# Iris and eye landmark indexes
LEFT_IRIS = [468, 469, 470, 471]
RIGHT_IRIS = [473, 474, 475, 476]

LEFT_EYE_TOP = 159
LEFT_EYE_BOTTOM = 145
RIGHT_EYE_TOP = 386
RIGHT_EYE_BOTTOM = 374

LEFT_EYE_CORNERS = [33, 133]
RIGHT_EYE_CORNERS = [362, 263]

mp_face_mesh = mp.solutions.face_mesh


# ============================================================
# ENGINE STATE
# ============================================================

_state_lock = threading.RLock()
_frame_lock = threading.Lock()

_face_mesh = None
_running = False

_stop_event = threading.Event()
_voice_thread = None

prev_x = SCREEN_W // 2
prev_y = SCREEN_H // 2

blink_start = None
typing_mode = False
cursor_locked = False

message = ""
message_time = 0.0
last_voice_text = ""

recognizer = sr.Recognizer()
recognizer.energy_threshold = 400
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 0.8

try:
    microphone = sr.Microphone()
except Exception as exc:
    microphone = None
    print("Microphone unavailable:", exc)


# ============================================================
# STATUS
# ============================================================

def show_message(text, duration=3):
    global message, message_time

    with _state_lock:
        message = str(text)
        message_time = time.time() + duration


def get_status():
    with _state_lock:
        return {
            "running": _running,
            "message": message if time.time() < message_time else "",
            "voice_available": microphone is not None,
            "typing_mode": typing_mode,
            "cursor_locked": cursor_locked,
            "last_voice_text": last_voice_text,
        }


def get_preview_status():
    return get_status()


# ============================================================
# FACE / IRIS HELPERS
# ============================================================

def eye_aspect_ratio(landmarks, top, bottom):
    return abs(landmarks[top].y - landmarks[bottom].y)


def get_iris_center(landmarks, indexes):
    points = np.array(
        [[landmarks[i].x, landmarks[i].y] for i in indexes],
        dtype=np.float32
    )
    return np.mean(points, axis=0)


def get_eye_horizontal_ratio(landmarks, iris_center, corners):
    x1 = landmarks[corners[0]].x
    x2 = landmarks[corners[1]].x

    low = min(x1, x2)
    high = max(x1, x2)

    return float((iris_center[0] - low) / max(high - low, 0.001))


def get_eye_vertical_ratio(landmarks, iris_center, top, bottom):
    y1 = landmarks[top].y
    y2 = landmarks[bottom].y

    low = min(y1, y2)
    high = max(y1, y2)

    return float((iris_center[1] - low) / max(high - low, 0.001))


# ============================================================
# SCREENSHOT / FILE HELPERS
# ============================================================

def take_screenshot():
    try:
        folder = os.path.join(
            os.path.expanduser("~"),
            "Pictures",
            "EYEVOX"
        )
        os.makedirs(folder, exist_ok=True)

        filename = time.strftime("EYEVOX_%Y%m%d_%H%M%S.png")
        filepath = os.path.join(folder, filename)

        pyautogui.screenshot().save(filepath)
        show_message("Screenshot saved")
        return filepath

    except Exception as exc:
        show_message(f"Screenshot error: {exc}", 4)
        return ""


def create_folder():
    try:
        path = os.path.join(
            os.path.expanduser("~"),
            "Desktop",
            "EYEVOX Folder"
        )
        os.makedirs(path, exist_ok=True)
        show_message("Folder created on Desktop")

    except Exception as exc:
        show_message(f"Folder error: {exc}", 4)


def create_text_file():
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        os.makedirs(desktop, exist_ok=True)

        path = os.path.join(
            desktop,
            f"EYEVOX_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        )

        with open(path, "w", encoding="utf-8") as file:
            file.write("Created using EYEVOX.")

        show_message("Text file created on Desktop")

    except Exception as exc:
        show_message(f"Text file error: {exc}", 4)


def create_word_file():
    try:
        from docx import Document

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        os.makedirs(desktop, exist_ok=True)

        path = os.path.join(
            desktop,
            f"EYEVOX_{time.strftime('%Y%m%d_%H%M%S')}.docx"
        )

        document = Document()
        document.add_heading("EYEVOX Document", 0)
        document.add_paragraph("Created using EYEVOX voice control.")
        document.save(path)

        show_message("Word document created on Desktop")

    except ImportError:
        show_message("Install python-docx first", 4)

    except Exception as exc:
        show_message(f"Word file error: {exc}", 4)


# ============================================================
# VOICE COMMANDS
# ============================================================

def handle_voice_command(command):
    global typing_mode, cursor_locked, last_voice_text

    command = command.lower().strip()

    if not command:
        return

    with _state_lock:
        last_voice_text = command

    print("EYEVOX recognized:", command)

    # Stop system
    if command in ("stop eyevox", "stop system", "exit eyevox"):
        stop_engine()
        return

    # Typing mode
    if command == "start typing":
        typing_mode = True
        show_message("Voice typing enabled")
        return

    if command == "stop typing":
        typing_mode = False
        show_message("Voice typing disabled")
        return

    # Cursor control
    if command == "lock cursor":
        cursor_locked = True
        show_message("Cursor locked")
        return

    if command == "unlock cursor":
        cursor_locked = False
        show_message("Cursor unlocked")
        return

    # Screenshot
    if command in ("take screenshot", "capture screenshot"):
        take_screenshot()
        return

    # File creation
    if command == "create folder":
        create_folder()
        return

    if command in ("create text file", "create txt file"):
        create_text_file()
        return

    if command in ("create word file", "create document"):
        create_word_file()
        return

    # Keyboard shortcuts
    keyboard_commands = {
        "press enter": ("key", "enter"),
        "new line": ("key", "enter"),
        "press space": ("key", "space"),
        "backspace": ("key", "backspace"),
        "delete character": ("key", "backspace"),
        "press tab": ("key", "tab"),
        "select all": ("hotkey", ["ctrl", "a"]),
        "copy": ("hotkey", ["ctrl", "c"]),
        "paste": ("hotkey", ["ctrl", "v"]),
        "cut": ("hotkey", ["ctrl", "x"]),
        "undo": ("hotkey", ["ctrl", "z"]),
        "save": ("hotkey", ["ctrl", "s"]),
        "save file": ("hotkey", ["ctrl", "s"]),
        "bold": ("hotkey", ["ctrl", "b"]),
        "italic": ("hotkey", ["ctrl", "i"]),
        "underline": ("hotkey", ["ctrl", "u"]),
    }

    if command in keyboard_commands:
        action, value = keyboard_commands[command]

        if action == "key":
            pyautogui.press(value)
        else:
            pyautogui.hotkey(*value)

        return

    if command == "period":
        pyautogui.write(".")
        return

    if command == "comma":
        pyautogui.write(",")
        return

    # Application commands
    if command in ("open notepad", "launch notepad"):
        subprocess.Popen(["notepad.exe"])
        show_message("Opening Notepad")
        return

    if command in ("open calculator", "launch calculator"):
        subprocess.Popen(["calc.exe"])
        show_message("Opening Calculator")
        return

    if command in ("open file explorer", "open explorer"):
        subprocess.Popen(["explorer.exe"])
        show_message("Opening File Explorer")
        return

    if command == "close window":
        pyautogui.hotkey("alt", "f4")
        show_message("Closing active window")
        return

    if command == "minimize window":
        pyautogui.hotkey("win", "down")
        show_message("Window minimized")
        return

    # In typing mode, recognized speech is typed as text.
    if typing_mode:
        pyautogui.write(command, interval=0.02)
        show_message("Voice text typed", 2)
        return

    show_message(f"Command not recognized: {command}", 3)


# ============================================================
# VOICE LISTENER
# ============================================================

def voice_listener():
    if microphone is None:
        show_message("Microphone unavailable", 4)
        return

    print("EYEVOX voice listener started")

    while not _stop_event.is_set():
        try:
            with microphone as source:
                try:
                    audio = recognizer.listen(
                        source,
                        timeout=1,
                        phrase_time_limit=VOICE_PHRASE_LIMIT
                    )
                except sr.WaitTimeoutError:
                    continue

            if _stop_event.is_set():
                break

            recognized = recognizer.recognize_google(audio)
            handle_voice_command(recognized)

        except sr.UnknownValueError:
            continue

        except sr.RequestError as exc:
            print("Google speech recognition error:", exc)
            show_message("Voice recognition needs internet", 4)
            time.sleep(2)

        except Exception as exc:
            if not _stop_event.is_set():
                print("Voice listener error:", exc)
                time.sleep(1)

    print("EYEVOX voice listener stopped")


# ============================================================
# START ENGINE
# ============================================================

def start_engine():
    global _face_mesh, _running, _voice_thread
    global blink_start, prev_x, prev_y

    with _state_lock:
        if _running:
            return "EYEVOX is already running"

        with _frame_lock:
            _face_mesh = mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )

        _stop_event.clear()
        _running = True

        blink_start = None
        prev_x = SCREEN_W // 2
        prev_y = SCREEN_H // 2

        if microphone is not None:
            _voice_thread = threading.Thread(
                target=voice_listener,
                daemon=True,
                name="EYEVOX-Voice"
            )
            _voice_thread.start()

        show_message("EYEVOX started successfully")
        print("EYEVOX engine started")

        return "EYEVOX started successfully"


# ============================================================
# STOP ENGINE
# ============================================================

def stop_engine():
    global _face_mesh, _running, _voice_thread, blink_start

    with _state_lock:
        if not _running and _face_mesh is None:
            return "EYEVOX is already stopped"

        _running = False
        _stop_event.set()
        blink_start = None

    with _frame_lock:
        if _face_mesh is not None:
            try:
                _face_mesh.close()
            except Exception as exc:
                print("FaceMesh close error:", exc)

            _face_mesh = None

    if (
        _voice_thread is not None
        and _voice_thread.is_alive()
        and threading.current_thread() != _voice_thread
    ):
        _voice_thread.join(timeout=2)

    _voice_thread = None

    show_message("EYEVOX stopped")
    print("EYEVOX engine stopped")

    return "EYEVOX stopped successfully"


# ============================================================
# PROCESS CAMERA FRAME
# ============================================================

def process_frame(jpeg_bytes):
    global prev_x, prev_y, blink_start

    with _state_lock:
        if not _running:
            return {
                "success": False,
                "running": False,
                "face_detected": False,
                "landmarks": [],
                "message": "EYEVOX is not running"
            }

    if not jpeg_bytes:
        return {
            "success": False,
            "message": "Empty camera frame",
            "face_detected": False,
            "landmarks": []
        }

    try:
        image_array = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if frame is None:
            raise ValueError("Invalid camera frame")

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        with _frame_lock:
            with _state_lock:
                if not _running or _face_mesh is None:
                    return {
                        "success": False,
                        "running": False,
                        "face_detected": False,
                        "landmarks": [],
                        "message": "EYEVOX is stopped"
                    }

                results = _face_mesh.process(rgb_frame)

        if not results.multi_face_landmarks:
            blink_start = None
            return {
                "success": True,
                "running": True,
                "face_detected": False,
                "landmarks": [],
                "message": "No face detected"
            }

        points = results.multi_face_landmarks[0].landmark

        left_iris = get_iris_center(points, LEFT_IRIS)
        right_iris = get_iris_center(points, RIGHT_IRIS)

        iris_x = float((left_iris[0] + right_iris[0]) / 2)
        iris_y = float((left_iris[1] + right_iris[1]) / 2)

        # Eye-relative gaze position.
        left_x_ratio = get_eye_horizontal_ratio(
            points, left_iris, LEFT_EYE_CORNERS
        )
        right_x_ratio = get_eye_horizontal_ratio(
            points, right_iris, RIGHT_EYE_CORNERS
        )

        gaze_x = (left_x_ratio + right_x_ratio) / 2

        left_y_ratio = get_eye_vertical_ratio(
            points, left_iris, LEFT_EYE_TOP, LEFT_EYE_BOTTOM
        )
        right_y_ratio = get_eye_vertical_ratio(
            points, right_iris, RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM
        )

        gaze_y = (left_y_ratio + right_y_ratio) / 2

        # Initial mapping range. Calibration may be needed for each user.
        gaze_x = float(np.clip((gaze_x - 0.25) / 0.50, 0, 1))
        gaze_y = float(np.clip((gaze_y - 0.20) / 0.60, 0, 1))

        # Blink detection
        left_opening = eye_aspect_ratio(
            points, LEFT_EYE_TOP, LEFT_EYE_BOTTOM
        )
        right_opening = eye_aspect_ratio(
            points, RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM
        )

        eye_opening = (left_opening + right_opening) / 2
        now = time.time()

        if eye_opening < BLINK_THRESHOLD:
            if blink_start is None:
                blink_start = now

        else:
            if blink_start is not None:
                duration = now - blink_start

                if duration >= SCREENSHOT_BLINK_TIME:
                    take_screenshot()

                elif duration >= CLICK_BLINK_TIME:
                    try:
                        pyautogui.click()
                        show_message("Blink click", 1)
                    except pyautogui.FailSafeException:
                        show_message("Mouse failsafe activated", 4)

                blink_start = None

            with _state_lock:
                can_move = _running and not cursor_locked

            if can_move:
                target_x = int(gaze_x * (SCREEN_W - 1))
                target_y = int(gaze_y * (SCREEN_H - 1))

                prev_x = int(
                    prev_x * (1 - SMOOTH_FACTOR)
                    + target_x * SMOOTH_FACTOR
                )

                prev_y = int(
                    prev_y * (1 - SMOOTH_FACTOR)
                    + target_y * SMOOTH_FACTOR
                )

                try:
                    pyautogui.moveTo(prev_x, prev_y)
                except pyautogui.FailSafeException:
                    show_message("Mouse failsafe activated", 4)

        return {
            "success": True,
            "running": True,
            "face_detected": True,
            "landmarks": [],
            "iris": {
                "x": iris_x,
                "y": iris_y
            },
            "gaze": {
                "x": gaze_x,
                "y": gaze_y
            },
            "eye_opening": float(eye_opening),
            "blink_detected": blink_start is not None,
            "last_voice_text": get_status()["last_voice_text"],
            "message": get_status()["message"]
        }

    except Exception as exc:
        print("Frame processing error:", exc)

        return {
            "success": False,
            "running": True,
            "face_detected": False,
            "landmarks": [],
            "message": str(exc)
        }
