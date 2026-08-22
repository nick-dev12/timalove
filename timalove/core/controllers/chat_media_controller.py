"""Compression et stockage des médias de conversation."""

from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, ImageOps

IMAGE_MAX_SIDE = 1280
IMAGE_QUALITY = 72
IMAGE_MAX_IN_BYTES = 8 * 1024 * 1024
VOICE_MAX_BYTES = 800 * 1024
VOICE_MAX_SECONDS = 60
ALLOWED_VOICE_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/mp4",
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/aac",
    "video/webm",
}


def compress_image_bytes(raw: bytes) -> bytes:
    img = Image.open(BytesIO(raw))
    img = ImageOps.exif_transpose(img)
    if img.mode in {"RGBA", "P"}:
        img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")
    width, height = img.size
    longest = max(width, height)
    if longest > IMAGE_MAX_SIDE:
        scale = IMAGE_MAX_SIDE / longest
        img = img.resize(
            (max(1, int(width * scale)), max(1, int(height * scale))),
            Image.Resampling.LANCZOS,
        )
    out = BytesIO()
    img.save(out, format="JPEG", quality=IMAGE_QUALITY, optimize=True)
    return out.getvalue()


def store_chat_image(profile_id, upload: UploadedFile) -> str:
    raw = upload.read()
    if not raw:
        raise ValueError("Image vide.")
    if len(raw) > IMAGE_MAX_IN_BYTES:
        raise ValueError("Image trop lourde (8 Mo max).")
    try:
        payload = compress_image_bytes(raw)
    except Exception as exc:
        raise ValueError("Image illisible.") from exc
    folder = Path(settings.MEDIA_ROOT) / "chat-photos"
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{profile_id}_{uuid.uuid4().hex[:12]}.jpg"
    (folder / filename).write_bytes(payload)
    return f"{settings.MEDIA_URL}chat-photos/{filename}"


def store_chat_voice(profile_id, upload: UploadedFile) -> str:
    raw = upload.read()
    if not raw:
        raise ValueError("Vocal vide.")
    if len(raw) > VOICE_MAX_BYTES:
        raise ValueError("Vocal trop lourd. Raccourcissez l’enregistrement.")
    content_type = (getattr(upload, "content_type", "") or "").split(";")[0].strip().lower()
    name = (upload.name or "voice.webm").lower()
    if content_type and content_type not in ALLOWED_VOICE_TYPES and not name.endswith(
        (".webm", ".ogg", ".m4a", ".mp3", ".mp4", ".wav", ".aac")
    ):
        raise ValueError("Format audio non pris en charge.")
    ext = "webm"
    if name.endswith(".ogg"):
        ext = "ogg"
    elif name.endswith(".m4a") or name.endswith(".mp4") or content_type == "audio/mp4":
        ext = "m4a"
    elif name.endswith(".mp3") or content_type == "audio/mpeg":
        ext = "mp3"
    folder = Path(settings.MEDIA_ROOT) / "chat-voice"
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{profile_id}_{uuid.uuid4().hex[:12]}.{ext}"
    (folder / filename).write_bytes(raw)
    return f"{settings.MEDIA_URL}chat-voice/{filename}"
