"""Save an uploaded resume safely into data/uploads/.

Safety rules:
- the user's filename is never used as a path (no "../" tricks): we pick a random name
- only .pdf and .txt, at most MAX_BYTES
- the content must match the extension (real PDF header, valid UTF-8 text)
- never overwrite an existing file
"""
import uuid
from pathlib import Path

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED = {".pdf", ".txt"}


class UploadError(ValueError):
    """The upload was refused; the message is safe to show to the user."""


def check_upload(filename: str, data: bytes) -> str:
    """Return the extension if the file is acceptable, else raise UploadError."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED:
        raise UploadError(f"Only PDF or TXT files are accepted (got '{ext or 'no extension'}').")
    if not data:
        raise UploadError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise UploadError(f"The file is too large ({len(data) // 1024} KB, max 5 MB).")
    if ext == ".pdf" and not data.startswith(b"%PDF-"):
        raise UploadError("This file has a .pdf name but is not a real PDF.")
    if ext == ".txt":
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise UploadError("This text file is not UTF-8 encoded.") from None
    return ext


def save_upload(filename: str, data: bytes) -> Path:
    """Check the file, then write it under a random name. Returns the saved path."""
    ext = check_upload(filename, data)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
    with open(path, "xb") as f:  # "x": fail instead of overwriting
        f.write(data)
    return path
