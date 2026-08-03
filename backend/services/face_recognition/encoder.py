import base64
import io

import numpy as np
from PIL import Image

from utils.logger import logger

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError as exc:  # dlib not compiled/installed for this Python/OS
    face_recognition = None
    FACE_RECOGNITION_AVAILABLE = False
    logger.warning(
        f"face_recognition/dlib not available ({exc}). "
        "Face recognition endpoints will return 503 until it is installed. "
        "See README 'Backend Setup' for CMake/build-tools requirements."
    )


def _require_face_recognition():
    if not FACE_RECOGNITION_AVAILABLE:
        raise RuntimeError(
            "face_recognition/dlib is not installed in this environment. "
            "Install CMake + a C++ build toolchain, then `pip install dlib face_recognition`."
        )


def decode_base64_image(image_base64: str) -> np.ndarray:
    """Accepts a raw base64 string or a data URL (data:image/jpeg;base64,...)."""
    if "," in image_base64[:100]:
        image_base64 = image_base64.split(",", 1)[1]
    raw = base64.b64decode(image_base64)
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    return np.array(image)


def extract_face_encoding(image_base64: str) -> np.ndarray | None:
    """Returns a single 128-d encoding for the largest face found, or None."""
    _require_face_recognition()
    image = decode_base64_image(image_base64)
    locations = face_recognition.face_locations(image, model="hog")
    if not locations:
        return None

    # pick the largest face box (closest to camera)
    def area(box):
        top, right, bottom, left = box
        return (bottom - top) * (right - left)

    locations.sort(key=area, reverse=True)
    encodings = face_recognition.face_encodings(image, known_face_locations=[locations[0]])
    if not encodings:
        return None
    return encodings[0]


def extract_multiple_encodings(images_base64: list[str]) -> list[list[float]]:
    """Used during registration — one encoding per uploaded sample image."""
    encodings: list[list[float]] = []
    for idx, img in enumerate(images_base64):
        try:
            enc = extract_face_encoding(img)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Failed to process registration image #{idx}: {exc}")
            continue
        if enc is not None:
            encodings.append(enc.tolist())
    return encodings


def detect_blink_liveness(images_sequence: list[str]) -> bool:
    """Lightweight liveness check: compares the eye-aspect-ratio proxy
    (vertical eye landmark distance) across a short frame sequence to
    detect a blink, guarding against a printed photo / static image spoof.
    """
    _require_face_recognition()
    ear_values = []
    for img_b64 in images_sequence:
        image = decode_base64_image(img_b64)
        landmarks_list = face_recognition.face_landmarks(image)
        if not landmarks_list:
            continue
        landmarks = landmarks_list[0]
        left_eye = landmarks.get("left_eye")
        if not left_eye or len(left_eye) < 6:
            continue
        top = np.mean([left_eye[1], left_eye[2]], axis=0)
        bottom = np.mean([left_eye[4], left_eye[5]], axis=0)
        horiz = np.linalg.norm(np.array(left_eye[0]) - np.array(left_eye[3]))
        vert = np.linalg.norm(top - bottom)
        if horiz > 0:
            ear_values.append(vert / horiz)

    if len(ear_values) < 2:
        return False

    return (max(ear_values) - min(ear_values)) > 0.06
