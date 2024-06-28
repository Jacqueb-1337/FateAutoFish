import sys
import time
import pyautogui
import pygetwindow as gw
import logging
import ctypes
from PyQt5 import QtWidgets, QtGui, QtCore
from threading import Thread, Event
import keyboard
import cv2
import numpy as np
import json
import os

if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

# Paths to resources
resume_game_path = os.path.join(application_path, 'resume_game.png')
ok_button_path = os.path.join(application_path, 'ok_button.png')
set_hook_path = os.path.join(application_path, 'set_hook.png')


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Coordinates for fishing spot and catching spot
fishing_spot = [806, 399]
catching_spot = [652, 555]

# Coordinates to check for the color change
color_check_location = [645, 344]

# Color to detect (hex: #e76517)
expected_color = (231, 101, 23)
tolerance = 30  # Tolerance for color matching

# Window title (or part of it) for the game
window_title = "Fate"

# Event to signal when the coordinates have been finalized
coords_finalized = Event()

# Flag to indicate script running state
script_running = True

# Get the path to the user's home directory
home_dir = os.path.expanduser("~")
config_path = os.path.join(home_dir, 'config.json')

def find_image_on_screen(image_path, threshold=0.8):
    screenshot = pyautogui.screenshot()
    screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
    template = cv2.imread(image_path, 0)
    if template is None:
        raise FileNotFoundError(f"Template image '{image_path}' not found.")
    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        x, y = max_loc
        return x + template.shape[1] // 2, y + template.shape[0] // 2
    else:
        return None

def save_config():
    config = {
        "fishing_spot": fishing_spot,
        "color_check_location": color_check_location,
        "catching_spot": catching_spot
    }
    with open(config_path, 'w') as config_file:
        json.dump(config, config_file)
    print(f"Configuration saved to {config_path}.")

def load_config():
    global fishing_spot, color_check_location, catching_spot
    try:
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
            fishing_spot = config.get("fishing_spot", fishing_spot)
            color_check_location = config.get("color_check_location", color_check_location)
            catching_spot = config.get("catching_spot", catching_spot)
    except FileNotFoundError:
        print("Config file not found, using default coordinates.")

class DraggableDot(QtWidgets.QLabel):
    def __init__(self, x, y, color, coord_var, overlay, parent=None):
        super().__init__('•', parent)
        self.coord_var = coord_var
        self.default_color = color
        self.selected_color = "white"
        self.selected = False
        self.overlay = overlay
        self.initUI(x, y)

    def initUI(self, x, y):
        self.setGeometry(x, y, 20, 20)
        self.setStyleSheet(f"color: {self.default_color}; font-size: 24px;")
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.show()

    def mousePressEvent(self, event):
        self.overlay.select_dot(self)
        event.accept()

    def set_selected(self, selected):
        self.selected = selected
        if self.selected:
            self.setStyleSheet(f"color: {self.default_color}; font-size: 24px; border: 2px solid {self.selected_color};")
        else:
            self.setStyleSheet(f"color: {self.default_color}; font-size: 24px;")

    def move_dot(self, dx, dy):
        x = self.x() + dx
        y = self.y() + dy
        self.move(x, y)
        self.coord_var[0], self.coord_var[1] = x, y

class Overlay(QtWidgets.QWidget):
    dotMoved = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setGeometry(0, 0, 1920, 1080)  # Adjust to your screen size
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.fishing_spot = fishing_spot
        self.color_check_location = color_check_location

        self.fishing_dot = DraggableDot(self.fishing_spot[0], self.fishing_spot[1], "red", self.fishing_spot, self, self)
        self.color_check_dot = DraggableDot(self.color_check_location[0], self.color_check_location[1], "green", self.color_check_location, self, self)

        self.selected_dot = None

        self.show()

    def select_dot(self, dot):
        if self.selected_dot and self.selected_dot != dot:
            self.selected_dot.set_selected(False)
        self.selected_dot = dot
        self.selected_dot.set_selected(True)

    def get_selected_dot(self):
        return self.selected_dot

    def move_dot(self, dx, dy, fine_movement=False):
        selected_dot = self.get_selected_dot()
        if selected_dot:
            move_by = 1 if fine_movement else 5
            selected_dot.move_dot(dx * move_by, dy * move_by)
            self.dotMoved.emit()

class ConsoleOverlay(QtWidgets.QWidget):
    appendText = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setGeometry(50, 50, 400, 200)  # Adjust to your screen size
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        self.setStyleSheet("background-color: black;")

        self.text_widget = QtWidgets.QTextEdit(self)
        self.text_widget.setGeometry(10, 10, 380, 180)
        self.text_widget.setStyleSheet("color: green; background-color: black; font-size: 12px;")
        self.text_widget.setReadOnly(True)

        self.appendText.connect(self.append_text)

        self.show()

    def append_text(self, text):
        self.text_widget.append(text)
        self.text_widget.ensureCursorVisible()

    def set_initial_message(self, message):
        self.text_widget.append(message)
        self.text_widget.ensureCursorVisible()

class TextHandler(logging.Handler):
    def __init__(self, console_overlay):
        super().__init__()
        self.console_overlay = console_overlay

    def emit(self, record):
        msg = self.format(record)
        if not any(suppressed_message in msg for suppressed_message in [
            "Checking if game is focused.",
            "Checking color at",
            "Current color at",
            "Color at",
            "COLOR MATCHED",
            "Screen size:"
        ]):
            self.console_overlay.appendText.emit(msg)

def move_selected_dot(dx, dy, fine_movement=False):
    overlay.move_dot(dx, dy, fine_movement)

def save_coords_and_continue():
    print(f"New fishing spot: {overlay.fishing_spot}")
    print(f"New color check location: {overlay.color_check_location}")
    save_config()
    overlay.close()
    coords_finalized.set()

def bring_window_to_foreground_and_press_esc(title):
    logging.info("Bringing window to foreground and pressing Esc.")
    windows = gw.getWindowsWithTitle(title)
    if windows:
        windows[0].activate()
        time.sleep(1)  # Increase delay to ensure the window is active
        # Use ctypes to press 'Esc'
        ctypes.windll.user32.keybd_event(0x1B, 0, 0, 0)  # 0x1B is the virtual key code for 'Esc'
        ctypes.windll.user32.keybd_event(0x1B, 0, 0x0002, 0)  # 0x0002 is the keyup flag
        logging.info("Switched to game window and pressed Esc.")
    else:
        logging.error(f"Window with title '{title}' not found.")

def get_pixel_color(x, y):
    try:
        # Get the screen size
        screen_width, screen_height = pyautogui.size()
        logging.info(f"Screen size: {screen_width}x{screen_height}")
        logging.info(f"Checking color at: {x}, {y}")
        
        # Ensure the coordinates are within screen bounds
        if x < 0 or x >= screen_width or y < 0 or y >= screen_height:
            raise ValueError("Coordinates are out of screen bounds")
        
        # Take a screenshot and get the color of the pixel at (x, y)
        screenshot = pyautogui.screenshot()
        color = screenshot.getpixel((x, y))
        logging.info(f"Color at {x}, {y}: {color}")
        return color
    except Exception as e:
        logging.error(f"Error getting pixel color: {e}")
        return None

def is_color_within_tolerance(color, target_color, tolerance):
    return all(abs(color[i] - target_color[i]) <= tolerance for i in range(3))

def click(x, y):
    ctypes.windll.user32.SetCursorPos(x, y)
    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
    time.sleep(0.01)
    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP

def check_and_click_resume_game():
    logging.info("Checking for 'Resume Game' on screen.")
    try:
        screenshot = pyautogui.screenshot()
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
        template = cv2.imread(resume_game_path, 0)
        if template is None:
            raise FileNotFoundError(f"Template image '{resume_game_path}' not found.")
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val > 0.8:  # Adjust the threshold as needed
            logging.info("'Resume Game' found on screen. Clicking it.")
            x, y = max_loc
            click(x + template.shape[1] // 2, y + template.shape[0] // 2)
            logging.info("Clicked 'Resume Game'.")
            return True
        logging.info("'Resume Game' not found on screen.")
    except Exception as e:
        logging.error(f"Error during template matching: {e}")
    return False

def check_and_click_ok_button():
    logging.info("Checking for 'OK Button' on screen.")
    try:
        screenshot = pyautogui.screenshot()
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
        template = cv2.imread(ok_button_path, 0)
        if template is None:
            raise FileNotFoundError(f"Template image '{ok_button_path}' not found.")
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val > 0.8:  # Adjust the threshold as needed
            logging.info("'OK Button' found on screen. Clicking it.")
            x, y = max_loc
            click(x + template.shape[1] // 2, y + template.shape[0] // 2)
            time.sleep(0.5)  # 500ms delay before the second click
            click(x + template.shape[1] // 2, y + template.shape[0] // 2)  # Second click
            logging.info("Clicked 'OK Button' twice.")
            return True
    except Exception as e:
        logging.error(f"Error during template matching: {e}")
    logging.info("'OK Button' not found on screen.")
    return False

def check_for_set_hook():
    logging.info("Checking for 'set_hook' on screen.")
    try:
        screenshot = pyautogui.screenshot()
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
        template = cv2.imread(set_hook_path, 0)
        if template is None:
            raise FileNotFoundError(f"Template image '{set_hook_path}' not found.")
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val > 0.8:  # Adjust the threshold as needed
            logging.info("'set_hook' found on screen.")
            return True
        logging.info("'set_hook' not found on screen.")
    except Exception as e:
        logging.error(f"Error during template matching: {e}")
    return False

def check_game_focus():
    logging.info("Checking if game is focused.")
    windows = gw.getWindowsWithTitle(window_title)
    if windows:
        return windows[0].isActive
    return False

def signal_handler():
    global script_running
    script_running = False
    logging.info("Script stopped by user.")
    keyboard.unhook_all()
    QtWidgets.QApplication.quit()
    os._exit(0)

def fish():
    logging.info("Starting fishing script.")
    bring_window_to_foreground_and_press_esc(window_title)
    time.sleep(1)  # Give some time for the window to come to the foreground

    if check_and_click_resume_game():
        time.sleep(2)  # Wait for the game to resume if "Resume Game" was clicked

    while script_running:
        if not check_game_focus():
            logging.info("Game window is not focused. Exiting script.")
            keyboard.unhook_all()
            QtWidgets.QApplication.quit()
            os._exit(0)

        logging.info("Checking for OK button or starting fishing.")
        while script_running:
            if check_and_click_ok_button():
                time.sleep(1)  # Give some time for the game to process the OK button click
            else:
                click(fishing_spot[0], fishing_spot[1])
                time.sleep(1)  # Wait for a short time before checking again
                if find_image_on_screen(set_hook_path):
                    logging.info("Started fishing. 'set_hook' detected.")
                    break

        logging.info("Waiting for pixel color change.")
        while script_running:
            if not check_game_focus():
                logging.info("Game window is not focused. Exiting script.")
                keyboard.unhook_all()
                QtWidgets.QApplication.quit()
                os._exit(0)

            current_color = get_pixel_color(*color_check_location)
            logging.info(f"Current color at {color_check_location}: {current_color}")
            if is_color_within_tolerance(current_color, expected_color, tolerance):
                logging.info("COLOR MATCHED, finding and clicking 'set_hook'")
                set_hook_coords = find_image_on_screen(set_hook_path)
                if set_hook_coords:
                    click(set_hook_coords[0], set_hook_coords[1])
                    time.sleep(0.2)  # 200ms delay before the second click
                    click(set_hook_coords[0], set_hook_coords[1])
                    logging.info("Caught a fish.")
                    break
            # Small delay to avoid overloading the CPU
            time.sleep(0.1)
        
        # Wait a bit before starting the next fishing action
        time.sleep(1)

def start_fishing():
    coords_finalized.wait()  # Wait for the coordinates to be finalized
    try:
        fish()
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    load_config()  # Load the config if it exists

    overlay = Overlay()
    overlay.setWindowTitle('Overlay')
    overlay.show()

    console_overlay = ConsoleOverlay()
    console_overlay.setWindowTitle('Console Overlay')
    console_overlay.show()

    # Set the initial message on the console overlay
    initial_message = (
        "Green dot represents the CENTER of the dot of the exclamation point above the player's head when a fish is on the line. "
        "Red dot represents the location of the area to click on to begin fishing.\n\n"
        "Click on one of the dots, then use W, A, S, and D to move the dot; you can also hold Shift to move it 1 pixel at a time.\n\n"
        "Use the TOP LEFT CORNER of the white square outline after selecting a dot to position each location.\n\n"
        "Press CTRL + S to save coordinates and continue, and CTRL + Q to stop the script."
    )
    console_overlay.set_initial_message(initial_message)

    # Redirect logging to the console overlay
    text_handler = TextHandler(console_overlay)
    logging.getLogger().addHandler(text_handler)

    fishing_thread = Thread(target=start_fishing)
    fishing_thread.start()

    # Hotkeys for moving the dots with suppression
    keyboard.add_hotkey('w', lambda: move_selected_dot(0, -1), suppress=True)
    keyboard.add_hotkey('s', lambda: move_selected_dot(0, 1), suppress=True)
    keyboard.add_hotkey('a', lambda: move_selected_dot(-1, 0), suppress=True)
    keyboard.add_hotkey('d', lambda: move_selected_dot(1, 0), suppress=True)

    # Hotkeys for fine movement with Shift + WASD
    keyboard.add_hotkey('shift+w', lambda: move_selected_dot(0, -1, fine_movement=True), suppress=True)
    keyboard.add_hotkey('shift+s', lambda: move_selected_dot(0, 1, fine_movement=True), suppress=True)
    keyboard.add_hotkey('shift+a', lambda: move_selected_dot(-1, 0, fine_movement=True), suppress=True)
    keyboard.add_hotkey('shift+d', lambda: move_selected_dot(1, 0, fine_movement=True), suppress=True)

    # Hotkey for saving coordinates and continuing
    keyboard.add_hotkey('ctrl+s', save_coords_and_continue, suppress=True)

    # Hotkey for stopping the script
    keyboard.add_hotkey('ctrl+q', signal_handler, suppress=True)

    sys.exit(app.exec_())
