import base64
from os import path

import cv2
import numpy as np


def load_all_templates() -> dict:
    all_templates = {}
    for digit in range(10):
        for font in ("b", "i"):
            template_name = str(digit) + font
            file_path = path.join("app", "img", f"{template_name}.png")
            if path.isfile(file_path):
                all_templates[template_name] = cv2.imread(file_path, -1)
            else:
                print(f"File {file_path} not found!")
    return all_templates


all_templates = load_all_templates()


def resolve_captcha(img_data: str) -> str:
    img_array = b64_to_array(img_data)
    digit_coordinates = digits_positions(img_array)
    captcha_txt = ""
    for _, char in sorted(digit_coordinates.items()):
        captcha_txt += char
    return captcha_txt


def b64_to_array(img_b64: str) -> np.ndarray:
    img_bytes = base64.b64decode(img_b64)
    img_buffer = np.frombuffer(img_bytes, dtype=np.uint8)
    return cv2.imdecode(img_buffer, cv2.IMREAD_UNCHANGED)


def digits_positions(img_array: np.ndarray) -> dict:
    digit_coordinates = {}
    for digit in range(10):
        digit_templates = (all_templates[f"{digit}b"], all_templates[f"{digit}i"])
        coordinates = match_digit(digit_templates, gray(img_array))
        for x_coord in coordinates:
            digit_coordinates[x_coord] = str(digit)
    return digit_coordinates


def match_digit(
    digit_templates: tuple[np.ndarray, np.ndarray], gray_img_array: np.ndarray
) -> list[np.int64]:
    # try_methods = [cv2.TM_SQDIFF_NORMED, cv2.TM_CCORR_NORMED, cv2.TM_CCOEFF_NORMED]
    method = cv2.TM_CCORR_NORMED
    threshhold = 0.99
    digit_coordinates = []
    for template in digit_templates:
        match_array = cv2.matchTemplate(gray_img_array, template, method)
        if method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
            char_positions = np.where(match_array <= 1 - threshhold)[1]
        else:
            char_positions = np.where(match_array >= threshhold)[1]
        digit_coordinates.extend(char_positions)
    return digit_coordinates


def gray(img_array: np.ndarray) -> np.ndarray:
    img_crop = img_array[5:][:][:]
    img_bwa = cv2.threshold(img_crop, 254, 255, cv2.THRESH_BINARY)[1]
    alpha_mask = img_bwa[:, :, 3] < 255
    img_bwa[alpha_mask] = [255, 255, 255, 255]
    return cv2.cvtColor(img_bwa, cv2.COLOR_BGRA2GRAY)
