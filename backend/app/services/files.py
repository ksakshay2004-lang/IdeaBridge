import os
import re
import uuid
from pathlib import Path
from typing import Tuple

from fastapi import HTTPException, UploadFile

from ..config import get_settings

ALLOWED = {
    ".pdf": (b"%PDF",), ".png": (b"\x89PNG\r\n\x1a\n",), ".jpg": (b"\xff\xd8\xff",), ".jpeg": (b"\xff\xd8\xff",),
    ".docx": (b"PK\x03\x04",), ".pptx": (b"PK\x03\x04",), ".txt": None,
}
CONTENT_TYPES = {
    ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation", ".txt": "text/plain",
}
MAX_DOCS_PER_IDEA = 10


def upload_root() -> Path:
    p = Path(get_settings().upload_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_filename(name: str) -> str:
    base = os.path.basename((name or "file").replace("\\", "/"))
    base = re.sub(r"[^\w.\- ]", "_", base).strip(" .") or "file"
    return base[:120]


async def save_upload(file: UploadFile) -> Tuple[str, int, str, str]:
    """Validate (extension, size, magic bytes) and store with a random name. Returns (stored, size, ctype, name)."""
    name = safe_filename(file.filename or "")
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED:
        raise HTTPException(415, f"File type not allowed. Allowed: {', '.join(sorted(ALLOWED))}")
    limit = get_settings().max_upload_mb * 1024 * 1024
    chunks, size = [], 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > limit:
            raise HTTPException(413, f"File too large (max {get_settings().max_upload_mb} MB)")
        chunks.append(chunk)
    data = b"".join(chunks)
    if size == 0:
        raise HTTPException(400, "File is empty")
    magics = ALLOWED[ext]
    if magics and not any(data.startswith(m) for m in magics):
        raise HTTPException(415, "File content does not match its extension")
    if ext == ".txt":
        try:
            data[:4096].decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(415, "Text files must be UTF-8") from None
        if b"\x00" in data[:4096]:
            raise HTTPException(415, "Text files must not contain binary data")
    stored = uuid.uuid4().hex + ext
    (upload_root() / stored).write_bytes(data)
    return stored, size, CONTENT_TYPES[ext], name


def delete_stored(stored_name: str) -> None:
    try:
        (upload_root() / os.path.basename(stored_name)).unlink(missing_ok=True)
    except OSError:
        pass
