# vision.py — Screenshot capture + OCR via pytesseract

import pyautogui
import pytesseract
from PIL import Image
from config import SCREENSHOT_PATH


class Vision:
    def capture_screenshot(self) -> Image.Image:
        """Take a full-screen screenshot and save it to disk."""
        screenshot = pyautogui.screenshot()
        screenshot.save(SCREENSHOT_PATH)
        return screenshot

    def get_screen_text(self) -> str:
        """
        Capture the current screen and return all visible text via OCR.
        Useful for letting the planner understand the current UI state.
        """
        image = self.capture_screenshot()
        text  = pytesseract.image_to_string(image)
        return text.strip()

    def get_screen_text_from_region(self, x: int, y: int,
                                    width: int, height: int) -> str:
        """OCR a specific screen region (x, y, width, height)."""
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        return pytesseract.image_to_string(screenshot).strip()
