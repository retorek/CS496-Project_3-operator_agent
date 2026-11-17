"""Read a resume file (.pdf or .txt) and return its plain text."""
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError


def read_pdf(path: Path) -> str:
    """Join the text of every page, one blank line between pages."""
    try:
        reader = PdfReader(path)
        pages = [page.extract_text() or "" for page in reader.pages]
    except PyPdfError as e:  # damaged or encrypted PDF
        raise ValueError(f"Could not read this PDF ({e}).") from e
    return "\n\n".join(pages).strip()


def read_resume(path: str | Path) -> str:
    """Pick the reader from the file extension; fail clearly on anything else."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = read_pdf(path)
    elif suffix == ".txt":
        text = path.read_text(encoding="utf-8").strip()
    else:
        raise ValueError(f"Unsupported resume format: {suffix} (use .pdf or .txt)")
    if not text:
        raise ValueError(f"No text found in {path.name} (scanned PDF?)")
    return text
