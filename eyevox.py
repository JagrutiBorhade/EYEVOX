import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time
import threading
import speech_recognition as sr
import queue
import os
import subprocess

# ---------------- SETTINGS ----------------
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

BLINK_THRESHOLD = 0.015
CLICK_BLINK_TIME = 0.15
SCREENSHOT_BLINK_TIME = 1.0
SMOOTH_FACTOR = 0.15
VOICE_PHRASE_LIMIT = 6

SCREEN_W, SCREEN_H = pyautogui.size()

# ---------------- MEDIAPIPE ----------------
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

LEFT_IRIS = [468, 469, 470, 471]
RIGHT_IRIS = [473, 474, 475, 476]

LEFT_EYE_TOP, LEFT_EYE_BOTTOM = 159, 145
RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM = 386, 374

# ---------------- STATE ----------------
prev_x, prev_y = SCREEN_W // 2, SCREEN_H // 2
blink_start = None
typing_mode = False
cursor_locked = False
listening = True

message = ""
message_time = 0

# ---------------- VOICE ----------------
cmd_queue = queue.Queue()
recognizer = sr.Recognizer()
recognizer.energy_threshold = 400
recognizer.dynamic_energy_threshold = False

try:
    microphone = sr.Microphone()
except Exception as exc:
    microphone = None
    print("Microphone not detected:", exc)


# ---------------- GET CURRENT FOLDER ----------------
def get_active_explorer_path():
    try:
        cmd = r'powershell "(New-Object -ComObject Shell.Application).Windows() | ForEach-Object { $_.Document.Folder.Self.Path }"'
        output = subprocess.check_output(
            cmd, shell=True, stderr=subprocess.DEVNULL
        )
        paths = output.decode(errors="ignore").strip().splitlines()

        if paths and paths[-1].strip():
            return paths[-1].strip()

    except Exception:
        pass

    return os.path.join(os.path.expanduser("~"), "Desktop")


# ---------------- UTILS ----------------
def show_message(text, duration=2):
    global message, message_time
    message = text
    message_time = time.time() + duration


def eye_aspect_ratio(lm, top, bottom):
    return abs(lm[top].y - lm[bottom].y)


def get_iris_center(lm, ids):
    pts = np.array([[lm[i].x, lm[i].y] for i in ids])
    return np.mean(pts, axis=0)


def focus_text_area():
    time.sleep(0.2)
    pyautogui.click()
    time.sleep(0.2)


def take_screenshot():
    screenshot_folder = os.path.join(os.getcwd(), "screenshots")
    os.makedirs(screenshot_folder, exist_ok=True)

    filename = f"screenshot_{int(time.time())}.png"
    path = os.path.join(screenshot_folder, filename)

    pyautogui.screenshot(path)
    show_message("Screenshot saved")


# ---------------- VOICE LISTENER ----------------
def voice_listener():
    if microphone is None:
        print("Voice listener unavailable: no microphone.")
        return

    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)

        print("Voice system ready. Speak a command.")

    except Exception as exc:
        print("Microphone setup failed:", exc)
        return

    while listening:
        try:
            with microphone as source:
                audio = recognizer.listen(
                    source,
                    phrase_time_limit=VOICE_PHRASE_LIMIT
                )

            text = recognizer.recognize_google(audio).lower().strip()
            print("VOICE:", text)

            if len(text) > 1:
                cmd_queue.put(text)

        except sr.UnknownValueError:
            pass

        except sr.RequestError as exc:
            print("Speech recognition service error:", exc)
            time.sleep(1)

        except Exception as exc:
            print("Voice input error:", exc)


# ---------------- HANDLE COMMAND ----------------
def handle_command(cmd):
    global typing_mode, cursor_locked, listening

    cmd = cmd.lower().strip()
    show_message(cmd)

    current_path = get_active_explorer_path()

    # START TYPING
    if "start typing" in cmd:
        typing_mode = True
        cursor_locked = True
        focus_text_area()
        show_message("Typing mode ON")
        return

    # STOP TYPING
    if "stop typing" in cmd:
        typing_mode = False
        cursor_locked = False
        show_message("Typing mode OFF")
        return

    # TYPING MODE
    if typing_mode:

        if cmd.startswith("bold"):
            pyautogui.hotkey("ctrl", "b")
            text = cmd.replace("bold", "", 1).strip()

            if text:
                pyautogui.write(text + " ")

            return

        if cmd.startswith("italic"):
            pyautogui.hotkey("ctrl", "i")
            text = cmd.replace("italic", "", 1).strip()

            if text:
                pyautogui.write(text + " ")

            return

        if cmd.startswith("underline"):
            pyautogui.hotkey("ctrl", "u")
            text = cmd.replace("underline", "", 1).strip()

            if text:
                pyautogui.write(text + " ")

            return

        if cmd == "backspace":
            pyautogui.press("backspace")
            return

        if cmd == "space":
            pyautogui.press("space")
            return

        if cmd in ("full stop", "period"):
            pyautogui.write(".")
            return

        if cmd == "comma":
            pyautogui.write(",")
            return

        if cmd == "new line":
            pyautogui.press("enter")
            return

        pyautogui.write(cmd + " ", interval=0.05)
        return

    # CREATE FOLDER
    if "create folder" in cmd:
        folder_name = cmd.replace("create folder", "", 1).strip()

        if folder_name:
            path = os.path.join(current_path, folder_name)
            os.makedirs(path, exist_ok=True)
            show_message("Folder created")
        else:
            show_message("Say create folder followed by a name")

        return

    # CREATE WORD FILE
    if "create word file" in cmd:
        filename = cmd.replace("create word file", "", 1).strip()

        if filename:
            if not filename.lower().endswith(".docx"):
                filename += ".docx"

            path = os.path.join(current_path, filename)

            try:
                from docx import Document

                Document().save(path)
                os.startfile(path)
                show_message("Word file created")

            except ImportError:
                show_message("Install python-docx")
                print("Run: py -3.11 -m pip install python-docx")

            except Exception as exc:
                show_message("Could not create Word file")
                print("Word file error:", exc)

        return

    # CREATE TEXT FILE
    if "create file" in cmd:
        filename = cmd.replace("create file", "", 1).strip()

        if filename:
            if "." not in filename:
                filename += ".txt"

            path = os.path.join(current_path, filename)

            with open(path, "a", encoding="utf-8"):
                pass

            os.startfile(path)
            show_message("Text file created")

        return

    # SAVE FILE
    if cmd in ("save", "save file"):
        pyautogui.hotkey("ctrl", "s")
        show_message("Save command sent")
        return

    # SAVE AS PDF
    if "save as pdf" in cmd:
        show_message("Use the application's Save As or Export to PDF")
        pyautogui.press("f12")
        return

    # OPEN SELECTED ITEM
    if "open selected" in cmd or cmd == "open it":
        pyautogui.press("enter")
        show_message("Opening selected item")
        return

    # DELETE SELECTED ITEM
    if "delete selected" in cmd or cmd == "delete":
        pyautogui.press("delete")
        show_message("Delete command sent")
        return

    # OPEN FILE EXPLORER
    if "open file explorer" in cmd:
        subprocess.Popen("explorer")
        show_message("Opening File Explorer")
        return

    # OPEN APPLICATION
    if cmd.startswith("open "):
        app = cmd.replace("open ", "", 1).strip()

        if app:
            pyautogui.press("win")
            time.sleep(0.8)
            pyautogui.write(app, interval=0.05)
            time.sleep(0.8)
            pyautogui.press("enter")
            show_message(f"Opening {app}")

        return

    # CLOSE WINDOW
    if cmd in ("close", "close window"):
        pyautogui.hotkey("alt", "f4")
        return

    # MINIMIZE WINDOW
    if cmd in ("minimize", "minimize window"):
        pyautogui.hotkey("win", "down")
        return

    # EXIT
    if cmd in ("stop", "exit", "quit"):
        listening = False
        show_message("Stopping system")


# ---------------- MAIN ----------------
def main():
    global prev_x, prev_y, blink_start, listening

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Camera not detected. Check camera access and try again.")
        return

    threading.Thread(
        target=voice_listener,
        daemon=True
    ).start()

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                print("Could not read from camera.")
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)
            now = time.time()

            if results.multi_face_landmarks:
                lm = results.multi_face_landmarks[0].landmark

                ear = (
                    eye_aspect_ratio(
                        lm, LEFT_EYE_TOP, LEFT_EYE_BOTTOM
                    )
                    + eye_aspect_ratio(
                        lm, RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM
                    )
                ) / 2

                if not typing_mode:
                    if ear < BLINK_THRESHOLD:
                        if blink_start is None:
                            blink_start = now

                    else:
                        if blink_start is not None:
                            duration = now - blink_start

                            if duration >= SCREENSHOT_BLINK_TIME:
                                take_screenshot()

                            elif duration >= CLICK_BLINK_TIME:
                                pyautogui.click()
                                show_message("Click")

                        blink_start = None

                left = get_iris_center(lm, LEFT_IRIS)
                right = get_iris_center(lm, RIGHT_IRIS)

                px = (left[0] + right[0]) / 2
                py = (left[1] + right[1]) / 2

                sx = np.interp(px, [0.35, 0.65], [0, SCREEN_W])
                sy = np.interp(py, [0.30, 0.70], [0, SCREEN_H])

                x = prev_x + (sx - prev_x) * SMOOTH_FACTOR
                y = prev_y + (sy - prev_y) * SMOOTH_FACTOR

                if not cursor_locked:
                    pyautogui.moveTo(x, y)

                prev_x, prev_y = x, y

            while not cmd_queue.empty():
                handle_command(cmd_queue.get())

            if time.time() < message_time:
                cv2.putText(
                    frame,
                    message,
                    (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (0, 0, 255),
                    2
                )

            cv2.imshow("Eye Voice System", frame)

            if cv2.waitKey(1) == 27 or not listening:
                break

    finally:
        listening = False
        cap.release()
        face_mesh.close()
        cv2.destroyAllWindows()


# ---------------- RUN ----------------
if __name__ == "__main__":
    main()