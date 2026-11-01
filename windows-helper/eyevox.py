import os
import time
import queue
import threading
import subprocess
import ctypes
import urllib.parse
import webbrowser

import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import speech_recognition as sr


# ---------------- SETTINGS ----------------
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0

BLINK_THRESHOLD = 0.015
CLICK_BLINK_TIME = 0.15
SCREENSHOT_BLINK_TIME = 1.0
SMOOTH_FACTOR = 0.15
VOICE_PHRASE_LIMIT = 6

SCREEN_W, SCREEN_H = pyautogui.size()

LEFT_IRIS = [468, 469, 470, 471]
RIGHT_IRIS = [473, 474, 475, 476]
LEFT_EYE_TOP, LEFT_EYE_BOTTOM = 159, 145
RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM = 386, 374

mp_face_mesh = mp.solutions.face_mesh

# ---------------- ENGINE STATE ----------------
_state_lock = threading.RLock()
_frame_lock = threading.Lock()

_face_mesh = None
_running = False

_stop_event = threading.Event()
_voice_thread = None

prev_x, prev_y = SCREEN_W // 2, SCREEN_H // 2

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
    print("Microphone not detected:", exc)


# ---------------- STATUS ----------------

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


# ---------------- EYE TRACKING HELPERS ----------------

def eye_aspect_ratio(landmarks, top, bottom):
    return abs(landmarks[top].y - landmarks[bottom].y)


def get_iris_center(landmarks, ids):
    points = np.array([
        [landmarks[i].x, landmarks[i].y]
        for i in ids
    ])

    return np.mean(points, axis=0)


def get_active_explorer_path():
    try:
        command = (
            r'powershell "(New-Object -ComObject Shell.Application).Windows() '
            r'| ForEach-Object { $_.Document.Folder.Self.Path }"'
        )

        output = subprocess.check_output(
            command,
            shell=True,
            stderr=subprocess.DEVNULL,
            timeout=3
        )

        paths = output.decode(errors="ignore").strip().splitlines()

        if paths and paths[-1].strip():
            return paths[-1].strip()

    except Exception:
        pass

    return os.path.join(os.path.expanduser("~"), "Desktop")


# ---------------- SCREENSHOT ----------------

def take_screenshot():
    try:
        screenshot_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "screenshots"
        )

        os.makedirs(screenshot_folder, exist_ok=True)

        filename = f"screenshot_{int(time.time())}.png"
        path = os.path.join(screenshot_folder, filename)

        pyautogui.screenshot(path)

        show_message(f"Screenshot saved: {filename}")

    except Exception as exc:
        show_message(f"Screenshot failed: {exc}")


# ---------------- TEXT INPUT ----------------

def _type_text(text):
    text = text.strip()

    if not text:
        return

    try:
        pyautogui.write(text, interval=0.015)

    except Exception:
        try:
            import pyperclip

            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")

        except Exception as exc:
            print("Text input error:", exc)
            show_message("Could not type text")


def _open_url(url, label):
    try:
        os.startfile(url)
        show_message(f"Opening {label}")

    except Exception as exc:
        print(f"Could not open {label}:", exc)
        show_message(f"Could not open {label}")


def _search_google(query):
    url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
    _open_url(url, f"Google search: {query}")


def _search_youtube(query):
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    _open_url(url, f"YouTube search: {query}")


# ---------------- WHATSAPP ----------------

def open_whatsapp():
    _open_url("https://web.whatsapp.com/", "WhatsApp Web")


def open_whatsapp_chat(number):
    number = "".join(ch for ch in number if ch.isdigit())

    if len(number) == 10:
        number = "91" + number

    if len(number) < 10:
        show_message("Please speak a valid phone number")
        return

    url = f"https://wa.me/{number}"
    _open_url(url, "WhatsApp chat")


def whatsapp_message(number, text):
    number = "".join(ch for ch in number if ch.isdigit())

    if len(number) == 10:
        number = "91" + number

    if len(number) < 10:
        show_message("Please speak a valid phone number")
        return

    encoded_text = urllib.parse.quote(text)
    url = f"https://wa.me/{number}?text={encoded_text}"

    _open_url(url, "WhatsApp message draft")
    show_message("Message prepared. Review it before sending.")


# ---------------- EMAIL ----------------

def compose_gmail(text=""):
    url = "https://mail.google.com/mail/u/0/#compose"

    if text:
        url += "?body=" + urllib.parse.quote(text)

    _open_url(url, "Gmail compose")


# ---------------- APPLICATIONS ----------------

def open_notepad():
    try:
        subprocess.Popen(["notepad.exe"])
        show_message("Opening Notepad")
    except Exception as exc:
        show_message(f"Notepad error: {exc}")


def new_notepad_file():
    try:
        subprocess.Popen(["notepad.exe"])
        show_message("Opening a new Notepad document")
    except Exception as exc:
        show_message(f"Could not open Notepad: {exc}")


def close_notepad():
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()

        if not hwnd:
            show_message("No active window")
            return

        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        title = ctypes.create_unicode_buffer(length + 1)

        ctypes.windll.user32.GetWindowTextW(
            hwnd,
            title,
            length + 1
        )

        if "notepad" not in title.value.lower():
            show_message("Notepad is not the active window")
            return

        ctypes.windll.user32.PostMessageW(
            hwnd,
            0x0010,
            0,
            0
        )

        show_message("Closing Notepad")

    except Exception as exc:
        show_message(f"Close error: {exc}")


def open_calculator():
    try:
        subprocess.Popen(["calc.exe"])
        show_message("Opening Calculator")
    except Exception as exc:
        show_message(f"Calculator error: {exc}")


def open_explorer():
    try:
        subprocess.Popen(["explorer.exe"])
        show_message("Opening File Explorer")
    except Exception as exc:
        show_message(f"Explorer error: {exc}")


def open_chrome():
    _open_url("https://www.google.com", "Google Chrome")


# ---------------- FILE CREATION ----------------

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
        show_message(f"Folder error: {exc}")


def create_text_file():
    try:
        desktop = os.path.join(
            os.path.expanduser("~"),
            "Desktop"
        )

        os.makedirs(desktop, exist_ok=True)

        filename = f"EYEVOX_{int(time.time())}.txt"
        path = os.path.join(desktop, filename)

        with open(path, "w", encoding="utf-8") as file:
            file.write("Created using EYEVOX.")

        os.startfile(path)
        show_message("Text file created and opened")

    except Exception as exc:
        show_message(f"Text file error: {exc}")


def create_word_file():
    try:
        from docx import Document

        desktop = os.path.join(
            os.path.expanduser("~"),
            "Desktop"
        )

        os.makedirs(desktop, exist_ok=True)

        filename = f"EYEVOX_{int(time.time())}.docx"
        path = os.path.join(desktop, filename)

        document = Document()
        document.add_heading("EYEVOX Document", 0)
        document.add_paragraph("Created using EYEVOX voice assistant.")
        document.save(path)

        os.startfile(path)
        show_message("Word document created and opened")

    except ImportError:
        show_message("Install python-docx to create Word files")

    except Exception as exc:
        show_message(f"Word file error: {exc}")


# ---------------- VOICE COMMAND ROUTER ----------------

def handle_command(command):
    global typing_mode, cursor_locked, last_voice_text

    cmd = " ".join(command.lower().strip().split())

    if not cmd:
        return

    with _state_lock:
        last_voice_text = cmd

    print("EYEVOX VOICE:", cmd)

    # ---- Dictation ----

    if cmd in (
        "start typing",
        "start dictation",
        "begin dictation",
        "dictation on"
    ):
        typing_mode = True
        cursor_locked = True
        show_message("Dictation started. Speak naturally.")
        return

    if cmd in (
        "stop typing",
        "stop dictation",
        "dictation off",
        "finish typing"
    ):
        typing_mode = False
        cursor_locked = False
        show_message("Dictation stopped")
        return

    # ---- Type a single sentence ----

    prefixes = (
        "type ",
        "write this ",
        "enter text ",
        "dictate "
    )

    for prefix in prefixes:
        if cmd.startswith(prefix):
            text = cmd[len(prefix):].strip()
            _type_text(text)
            show_message("Text typed")
            return

    # ---- Website commands ----

    if cmd in ("open whatsapp", "launch whatsapp", "start whatsapp"):
        open_whatsapp()
        return

    if cmd in ("open google", "launch google", "go to google"):
        _open_url("https://www.google.com", "Google")
        return

    if cmd in ("open youtube", "launch youtube", "go to youtube"):
        _open_url("https://www.youtube.com", "YouTube")
        return

    if cmd in ("open chatgpt", "launch chatgpt", "open chat gpt"):
        _open_url("https://chatgpt.com/", "ChatGPT")
        return

    if cmd in ("open gmail", "launch gmail", "check gmail"):
        _open_url("https://mail.google.com/", "Gmail")
        return

    if cmd in ("open instagram", "launch instagram"):
        _open_url("https://www.instagram.com/", "Instagram")
        return

    if cmd in ("open facebook", "launch facebook"):
        _open_url("https://www.facebook.com/", "Facebook")
        return

    if cmd in ("open linkedin", "launch linkedin"):
        _open_url("https://www.linkedin.com/", "LinkedIn")
        return

    if cmd in ("open github", "launch github"):
        _open_url("https://github.com/", "GitHub")
        return

    if cmd in ("open spotify", "launch spotify"):
        _open_url("https://open.spotify.com/", "Spotify")
        return

    if cmd in ("open amazon", "launch amazon"):
        _open_url("https://www.amazon.in/", "Amazon")
        return

    if cmd in ("open maps", "open google maps"):
        _open_url("https://maps.google.com/", "Google Maps")
        return

    # ---- Search commands ----

    if cmd.startswith("search google for "):
        query = cmd.replace("search google for ", "", 1).strip()
        if query:
            _search_google(query)
        return

    if cmd.startswith("google search "):
        query = cmd.replace("google search ", "", 1).strip()
        if query:
            _search_google(query)
        return

    if cmd.startswith("search youtube for "):
        query = cmd.replace("search youtube for ", "", 1).strip()
        if query:
            _search_youtube(query)
        return

    if cmd.startswith("youtube search "):
        query = cmd.replace("youtube search ", "", 1).strip()
        if query:
            _search_youtube(query)
        return

    # ---- WhatsApp commands ----

    if cmd.startswith("open whatsapp chat "):
        number = cmd.replace("open whatsapp chat ", "", 1)
        open_whatsapp_chat(number)
        return

    if cmd.startswith("whatsapp chat "):
        number = cmd.replace("whatsapp chat ", "", 1)
        open_whatsapp_chat(number)
        return

    if cmd.startswith("whatsapp message "):
        # Example:
        # whatsapp message 9876543210 saying hello how are you
        content = cmd.replace("whatsapp message ", "", 1)

        if " saying " in content:
            number, text = content.split(" saying ", 1)
            whatsapp_message(number, text)
        else:
            show_message("Say: WhatsApp message NUMBER saying MESSAGE")

        return

    # ---- Gmail compose ----

    if cmd.startswith("compose email saying "):
        text = cmd.replace("compose email saying ", "", 1)
        compose_gmail(text)
        return

    if cmd in ("compose email", "write email", "new email"):
        compose_gmail()
        return

    # ---- Notepad commands ----

    if cmd in ("open notepad", "launch notepad", "start notepad"):
        open_notepad()
        return

    if cmd in (
        "open new file",
        "new file",
        "create new file",
        "new notepad file"
    ):
        new_notepad_file()
        return

    if cmd in ("close notepad", "exit notepad"):
        close_notepad()
        return

    # ---- Desktop applications ----

    if cmd in ("open calculator", "launch calculator"):
        open_calculator()
        return

    if cmd in ("open file explorer", "open explorer"):
        open_explorer()
        return

    if cmd in ("open browser", "open chrome"):
        open_chrome()
        return

    # ---- File commands ----

    if cmd in ("create folder", "make folder", "new folder"):
        create_folder()
        return

    if cmd in ("create text file", "create txt file"):
        create_text_file()
        return

    if cmd in ("create word file", "create document"):
        create_word_file()
        return

    # ---- Browser and window commands ----

    if cmd in ("go back", "browser back"):
        pyautogui.hotkey("alt", "left")
        show_message("Going back")
        return

    if cmd in ("go forward", "browser forward"):
        pyautogui.hotkey("alt", "right")
        show_message("Going forward")
        return

    if cmd in ("refresh page", "reload page"):
        pyautogui.press("f5")
        show_message("Refreshing page")
        return

    if cmd in ("close tab", "close browser tab"):
        pyautogui.hotkey("ctrl", "w")
        show_message("Closing tab")
        return

    if cmd in ("new tab", "open new tab"):
        pyautogui.hotkey("ctrl", "t")
        show_message("New tab opened")
        return

    if cmd in ("scroll down", "page down"):
        pyautogui.scroll(-5)
        return

    if cmd in ("scroll up", "page up"):
        pyautogui.scroll(5)
        return

    if cmd in ("scroll to top", "go to top"):
        pyautogui.hotkey("ctrl", "home")
        return

    if cmd in ("scroll to bottom", "go to bottom"):
        pyautogui.hotkey("ctrl", "end")
        return

    # ---- Keyboard-free voice interaction commands ----
    # These commands are voice activated but use OS input simulation.

    if cmd in ("new line", "next line"):
        pyautogui.press("enter")
        return

    if cmd in ("new paragraph", "paragraph"):
        pyautogui.press("enter", presses=2, interval=0.1)
        return

    if cmd in ("space", "insert space"):
        pyautogui.press("space")
        return

    if cmd in ("select all",):
        pyautogui.hotkey("ctrl", "a")
        return

    if cmd == "copy":
        pyautogui.hotkey("ctrl", "c")
        return

    if cmd == "paste":
        pyautogui.hotkey("ctrl", "v")
        return

    if cmd == "cut":
        pyautogui.hotkey("ctrl", "x")
        return

    if cmd == "undo":
        pyautogui.hotkey("ctrl", "z")
        return

    if cmd == "redo":
        pyautogui.hotkey("ctrl", "y")
        return

    if cmd in ("save file", "save document"):
        pyautogui.hotkey("ctrl", "s")
        return

    if cmd in ("take screenshot", "capture screen"):
        take_screenshot()
        return

    if cmd in ("lock cursor", "freeze cursor"):
        cursor_locked = True
        show_message("Cursor paused")
        return

    if cmd in ("unlock cursor", "resume cursor"):
        cursor_locked = False
        show_message("Cursor resumed")
        return

    if cmd in ("minimize window",):
        pyautogui.hotkey("win", "down")
        return

    if cmd in ("maximize window",):
        pyautogui.hotkey("win", "up")
        return

    if cmd in ("close window",):
        pyautogui.hotkey("alt", "f4")
        return

    if cmd in ("switch window", "next window"):
        pyautogui.hotkey("alt", "tab")
        return

    # ---- Punctuation ----

    punctuation = {
        "full stop": ".",
        "period": ".",
        "comma": ",",
        "question mark": "?",
        "exclamation mark": "!",
        "colon": ":",
        "semicolon": ";",
        "open bracket": "(",
        "close bracket": ")",
        "at the rate": "@",
        "hashtag": "#",
    }

    if cmd in punctuation:
        _type_text(punctuation[cmd])
        return

    # ---- Dictation fallback ----

    if typing_mode:
        _type_text(command)
        show_message("Voice text entered", 2)
        return

    show_message(
        f"Command not recognized: {command}",
        3
    )


# ---------------- VOICE LISTENER ----------------

def voice_listener():
    if microphone is None:
        show_message("Microphone unavailable")
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
            handle_command(recognized)

        except sr.UnknownValueError:
            continue

        except sr.RequestError as exc:
            print("Speech recognition error:", exc)
            show_message("Speech recognition needs internet", 4)
            time.sleep(2)

        except Exception as exc:
            if not _stop_event.is_set():
                print("Voice listener error:", exc)
                time.sleep(1)

    print("EYEVOX voice listener stopped")


# ---------------- START ENGINE ----------------

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

        show_message("EYEVOX started")
        print("EYEVOX engine started")

        return "EYEVOX started successfully"


# ---------------- STOP ENGINE ----------------

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


# ---------------- PROCESS CAMERA FRAME ----------------

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
        image_array = np.frombuffer(
            jpeg_bytes,
            dtype=np.uint8
        )

        frame = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR
        )

        if frame is None:
            raise ValueError("Invalid camera frame")

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

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

        # Iris positions
        left_iris = get_iris_center(points, LEFT_IRIS)
        right_iris = get_iris_center(points, RIGHT_IRIS)

        raw_gaze_x = float(
            (left_iris[0] + right_iris[0]) / 2
        )

        raw_gaze_y = float(
            (left_iris[1] + right_iris[1]) / 2
        )

        # Original direct mapping; no calibration
        gaze_x = float(
            np.clip((raw_gaze_x - 0.25) / 0.50, 0.0, 1.0)
        )

        gaze_y = float(
            np.clip((raw_gaze_y - 0.20) / 0.60, 0.0, 1.0)
        )

        # Blink detection
        left_opening = eye_aspect_ratio(
            points,
            LEFT_EYE_TOP,
            LEFT_EYE_BOTTOM
        )

        right_opening = eye_aspect_ratio(
            points,
            RIGHT_EYE_TOP,
            RIGHT_EYE_BOTTOM
        )

        eye_opening = (
            left_opening + right_opening
        ) / 2

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
                        show_message("Mouse failsafe activated", 3)

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
                    show_message("Mouse failsafe activated", 3)

        status = get_status()

        return {
            "success": True,
            "running": True,
            "face_detected": True,
            "landmarks": [],
            "gaze": {
                "x": gaze_x,
                "y": gaze_y
            },
            "eye_opening": float(eye_opening),
            "blink_detected": blink_start is not None,
            "calibrated": True,
            "calibration_active": False,
            "calibration_points": 0,
            "last_voice_text": status["last_voice_text"],
            "message": status["message"]
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