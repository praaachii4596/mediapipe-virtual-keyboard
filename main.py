import tkinter as tk
from PIL import Image, ImageTk
import cv2
import mediapipe as mp
import ctypes
import math
from pynput.keyboard import Controller, Key
from time import time

# Windows API constants for click-through window
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20

def make_window_clickthrough(hwnd):
    styles = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, styles | WS_EX_LAYERED | WS_EX_TRANSPARENT)

print("Starting...")

# Mediapipe hands setup
mpHands = mp.solutions.hands
Hands = mpHands.Hands()
mpDraw = mp.solutions.drawing_utils

keyboard = Controller()

keys = [
    ["1","2","3","4","5","6","7","8","9","0","<-"],
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
    ["A", "S", "D", "F", "G", "H", "J", "K", "L", ";"],
    ["Shift","Z", "X", "C", "V", "B", "N", "M", ",", ".", "/"],
    ["Space"]
]

class Store():
    def __init__(self, pos, size, text):
        self.pos = pos
        self.size = size
        self.text = text
        self.pressed = False

# Layout parameters
key_width = 47
key_height = 45
spacing_x = 8
spacing_y = 10
top_margin = 20
window_width = 650
window_height = 500

# Dynamically position keys with top margin and centered rows
StoredVar = []
for i, row in enumerate(keys):
    total_width = 0
    widths = []
    for key in row:
        w = key_width
        if key == "Shift":
            w = int(key_width * 1.5)
        elif key == "Space":
            w = key_width * 6
        widths.append(w)
        total_width += w
    total_width += spacing_x * (len(row) - 1)

    x = (window_width - total_width) // 2
    y = top_margin + (key_height + spacing_y) * i

    for idx, key in enumerate(row):
        w = widths[idx]
        StoredVar.append(Store([x, y], [w, key_height], key))
        x += w + spacing_x

root = tk.Tk()
root.overrideredirect(True)
root.geometry(f"{window_width}x{window_height}")
root.attributes("-topmost", True)

hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
make_window_clickthrough(hwnd)

label = tk.Label(root)
label.pack()

# Enable dragging of the window
def start_move(event):
    root.x = event.x
    root.y = event.y

def do_move(event):
    x = root.winfo_pointerx() - root.x
    y = root.winfo_pointery() - root.y
    root.geometry(f"+{x}+{y}")

root.bind("<ButtonPress-1>", start_move)
root.bind("<B1-Motion>", do_move)

cap = cv2.VideoCapture(0)

shift_pressed = False
last_click_time = 0
click_delay = 0.8  # debounce time

def draw_rounded_rect(img, p1, p2, color, radius=10, thickness=-1):
    overlay = img.copy()
    x1, y1 = map(int, p1)
    x2, y2 = map(int, p2)
    cv2.rectangle(overlay, (x1 + radius, y1), (x2 - radius, y2), color, thickness)
    cv2.rectangle(overlay, (x1, y1 + radius), (x2, y2 - radius), color, thickness)
    cv2.circle(overlay, (x1 + radius, y1 + radius), radius, color, thickness)
    cv2.circle(overlay, (x2 - radius, y1 + radius), radius, color, thickness)
    cv2.circle(overlay, (x1 + radius, y2 - radius), radius, color, thickness)
    cv2.circle(overlay, (x2 - radius, y2 - radius), radius, color, thickness)
    alpha = 0.3
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)

def draw_buttons(img):
    for button in StoredVar:
        x, y = map(int, button.pos)
        w, h = map(int, button.size)

        base_color = (147, 112, 219)

        if button.pressed:
            fill_color = (0, 255, 0)  # Green for pressed key
            draw_rounded_rect(img, (x, y), (x + w, y + h), fill_color, radius=10)
            cv2.rectangle(img, (x, y), (x + w, y + h), fill_color, thickness=2)
        else:
            draw_rounded_rect(img, (x, y), (x + w, y + h), base_color, radius=10)
            cv2.rectangle(img, (x, y), (x + w, y + h), base_color, thickness=2)

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2
        text_color = (255, 255, 255)
        (text_w, text_h), _ = cv2.getTextSize(button.text, font, font_scale, thickness)
        text_x = x + (w - text_w) // 2
        text_y = y + (h + text_h) // 2 - 5

        cv2.putText(img, button.text, (text_x, text_y), font, font_scale, text_color, thickness)

def handle_key_press(key_text):
    global shift_pressed

    if key_text == "Shift":
        shift_pressed = not shift_pressed
        print(f"Shift {'activated' if shift_pressed else 'deactivated'}")
    elif key_text == "<-":
        keyboard.press(Key.backspace)
        keyboard.release(Key.backspace)
    elif key_text == "Space":
        keyboard.press(Key.space)
        keyboard.release(Key.space)
    else:
        if shift_pressed:
            keyboard.press(key_text.upper())
            keyboard.release(key_text.upper())
            shift_pressed = False  # disable shift after press
        else:
            keyboard.press(key_text.lower())
            keyboard.release(key_text.lower())

def update_frame():
    global last_click_time
    success, img = cap.read()
    if not success:
        root.after(10, update_frame)
        return

    img = cv2.flip(img, 1)
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = Hands.process(imgRGB)
    lmList = []

    if results.multi_hand_landmarks:
        for hand_landmark in results.multi_hand_landmarks:
            mpDraw.draw_landmarks(img, hand_landmark, mpHands.HAND_CONNECTIONS)
        for id, lm in enumerate(results.multi_hand_landmarks[0].landmark):
            h, w, c = img.shape
            cx, cy = int(lm.x * w), int(lm.y * h)
            lmList.append([cx, cy])

    for button in StoredVar:
        button.pressed = False

    click_threshold = 70
    cooldown = time() - last_click_time < click_delay

    if lmList and not cooldown:
        for button in StoredVar:
            x, y = map(int, button.pos)
            w, h = map(int, button.size)
            if x < lmList[8][0] < x + w and y < lmList[8][1] < y + h:
                x1, y1 = lmList[8]
                x2, y2 = lmList[12]
                dist = math.hypot(x2 - x1, y2 - y1)

                if dist < click_threshold:
                    handle_key_press(button.text)
                    button.pressed = True
                    last_click_time = time()
                    break

    draw_buttons(img)

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(img)
    imgtk = ImageTk.PhotoImage(image=img)
    label.imgtk = imgtk
    label.configure(image=imgtk)

    root.after(10, update_frame)

def on_key_press(event):
    if event.keysym == 'Escape':
        cap.release()
        root.destroy()

root.bind('<KeyPress>', on_key_press)

def on_closing():
    cap.release()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

update_frame()
root.mainloop()
cap.release()
