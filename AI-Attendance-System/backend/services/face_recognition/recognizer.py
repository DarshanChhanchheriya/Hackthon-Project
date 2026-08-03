import numpy as np
import face_recognition

from config import get_settings
from database import get_supabase
from services.face_recognition.encoder import extract_face_encoding
from utils.logger import logger

settings = get_settings()


def _confidence_from_distance(distance: float) -> float:
    """Maps a face-distance (0 = identical, ~0.6 = the standard face_recognition
    same-person cutoff) to a 0-100 confidence score.

    Distances above the tolerance are clipped to 0. Note: dividing by the
    tolerance here (instead of using the raw distance) previously made high
    confidence scores nearly unreachable — a genuine same-person distance of
    ~0.35-0.45 (completely normal for a webcam under different lighting than
    enrollment) scored only ~20-40%, well under the 90% match threshold, so
    real matches were silently rejected as "not recognized".
    """
    if distance > settings.FACE_DISTANCE_TOLERANCE:
        return 0.0
    confidence = (1 - distance) * 100
    return round(max(0.0, min(confidence, 100.0)), 2)


def load_known_faces(department_id: str | None = None) -> tuple[list[np.ndarray], list[dict]]:
    """Loads all stored student encodings (optionally scoped to a
    department) and their owning student metadata, for comparison against
    a live frame captured by a teacher running a recognition session.
    """
    supabase = get_supabase()
    rows = supabase.table("face_encodings").select("owner_id, encoding").execute().data or []
    if not rows:
        return [], []

    student_rows = (
        supabase.table("students")
        .select("id, roll_number, department_id, profiles(full_name), departments(name)")
        .execute()
        .data
        or []
    )
    student_map = {s["id"]: s for s in student_rows}

    encodings, meta = [], []
    for row in rows:
        student = student_map.get(row["owner_id"])
        if not student:
            continue  # encoding belongs to a teacher, not a student
        if department_id and student.get("department_id") != department_id:
            continue
        encodings.append(np.array(row["encoding"]))
        meta.append(
            {
                "student_id": student["id"],
                "roll_number": student.get("roll_number"),
                "full_name": (student.get("profiles") or {}).get("full_name"),
                "department": (student.get("departments") or {}).get("name"),
            }
        )
    return encodings, meta


def recognize_face(image_base64: str, department_id: str | None = None) -> dict:
    """Compares a live captured frame against all enrolled students and
    returns the best match with a confidence score, or a no-match result.
    """
    live_encoding = extract_face_encoding(image_base64)
    if live_encoding is None:
        return {"matched": False, "message": "No face detected in frame"}

    known_encodings, known_meta = load_known_faces(department_id)
    if not known_encodings:
        return {"matched": False, "message": "No enrolled faces to compare against"}

    distances = face_recognition.face_distance(known_encodings, live_encoding)
    best_idx = int(np.argmin(distances))
    best_distance = float(distances[best_idx])
    confidence = _confidence_from_distance(best_distance)

    logger.info(f"Face match candidate distance={best_distance:.4f} confidence={confidence}")

    if confidence < settings.FACE_MATCH_THRESHOLD * 100:
        return {
            "matched": False,
            "confidence": confidence,
            "message": "Face not recognized with sufficient confidence",
        }

    match = known_meta[best_idx]
    return {
        "matched": True,
        "student_id": match["student_id"],
        "full_name": match["full_name"],
        "roll_number": match["roll_number"],
        "department": match["department"],
        "confidence": confidence,
        "message": "Face recognized",
    }


def verify_self(image_base64: str, owner_id: str) -> dict:
    """Compares a live captured frame ONLY against the requesting user's own
    stored face encodings — used for self-service check-in (student marking
    their own attendance) and teacher punch-in/out, where the identity is
    already known and we're just confirming liveness/ownership, not
    searching the whole enrolled population.
    """
    live_encoding = extract_face_encoding(image_base64)
    if live_encoding is None:
        return {"matched": False, "message": "No face detected in frame"}

    supabase = get_supabase()
    rows = (
        supabase.table("face_encodings").select("encoding").eq("owner_id", owner_id).execute().data or []
    )
    if not rows:
        return {"matched": False, "message": "No face enrolled for this account yet"}

    known_encodings = [np.array(r["encoding"]) for r in rows]
    distances = face_recognition.face_distance(known_encodings, live_encoding)
    best_distance = float(np.min(distances))
    confidence = _confidence_from_distance(best_distance)

    if confidence < settings.FACE_MATCH_THRESHOLD * 100:
        return {
            "matched": False,
            "confidence": confidence,
            "message": "Face did not match your enrolled photos closely enough",
        }

    return {"matched": True, "confidence": confidence, "message": "Face verified"}
