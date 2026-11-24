"""
utils/text_extract.py
Pulls raw text out of an uploaded PDF, DOCX, or PPTX so the AI has real content to work from
instead of guessing. Images (including handwritten notes) return no extracted text here — they're
sent to a vision-capable model directly instead of being OCR'd locally.

Every failure mode a student can cause (wrong extension, renamed file, corrupt or password-protected
document, scanned PDF with no text layer) is converted to a ValueError with a plain-language message,
so routes can return a clean 400/422 instead of a 500.
"""
import io

MAX_CHARS = 20000  # keep prompts a sane size regardless of how big the source file is
SUPPORTED = ("pdf", "docx", "pptx", "jpg", "jpeg", "png", "webp")
UNSUPPORTED_MSG = "Unsupported file type. Please upload a PDF, DOCX, PPTX, JPG, PNG or WEBP file."


def file_extension(filename: str) -> str:
    return (filename.rsplit(".", 1)[-1] if filename and "." in filename else "").lower()


def _signature_ok(ext: str, content: bytes) -> bool:
    """A renamed .exe or a text file called notes.pdf must not get through on extension alone."""
    if ext == "pdf":
        return content[:1024].lstrip().startswith(b"%PDF")
    if ext in ("docx", "pptx"):
        return content[:4] == b"PK\x03\x04"
    if ext in ("jpg", "jpeg"):
        return content[:3] == b"\xff\xd8\xff"
    if ext == "png":
        return content[:8] == b"\x89PNG\r\n\x1a\n"
    if ext == "webp":
        return content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    return False


def _pdf_text(content: bytes) -> str:
    import pypdf
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            try:
                if not reader.decrypt(""):
                    raise ValueError("This PDF is password-protected. Remove the password and upload it again.")
            except ValueError:
                raise
            except Exception:
                raise ValueError("This PDF is password-protected. Remove the password and upload it again.")
        pages = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                pages.append("")   # one unreadable page shouldn't sink the whole document
        return "\n".join(pages)
    except ValueError:
        raise
    except Exception:
        raise ValueError("Couldn't read this PDF — it may be corrupted. Try re-exporting it and uploading again.")


def _docx_text(content: bytes) -> str:
    import docx
    try:
        document = docx.Document(io.BytesIO(content))
        parts = [p.text for p in document.paragraphs]
        for table in document.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))
        return "\n".join(parts)
    except Exception:
        raise ValueError("Couldn't read this Word document — it may be corrupted or not a real .docx file.")


def _pptx_shape_text(shape, out: list) -> None:
    if getattr(shape, "has_text_frame", False) and shape.text_frame and shape.text_frame.text.strip():
        out.append(shape.text_frame.text)
    if getattr(shape, "has_table", False) and shape.has_table:
        for row in shape.table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                out.append(" | ".join(cells))
    if getattr(shape, "shapes", None) is not None:   # grouped shapes
        for child in shape.shapes:
            _pptx_shape_text(child, out)


def _pptx_text(content: bytes) -> str:
    from pptx import Presentation
    try:
        prs = Presentation(io.BytesIO(content))
        chunks: list[str] = []
        for slide in prs.slides:
            for shape in slide.shapes:
                _pptx_shape_text(shape, chunks)
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame is not None:
                notes = slide.notes_slide.notes_text_frame.text.strip()
                if notes:
                    chunks.append(notes)
        return "\n".join(chunks)
    except Exception:
        raise ValueError("Couldn't read this PowerPoint — it may be corrupted or not a real .pptx file.")


def extract_text(filename: str, content: bytes) -> tuple[str, str]:
    """Returns (extracted_text, kind) where kind is 'text' or 'image'. Raises ValueError with a friendly message."""
    ext = file_extension(filename)
    if ext not in SUPPORTED:
        raise ValueError(UNSUPPORTED_MSG)
    if not _signature_ok(ext, content):
        raise ValueError(f"This file doesn't look like a real .{ext} file. Please check it and upload again.")

    if ext in ("jpg", "jpeg", "png", "webp"):
        return "", "image"
    if ext == "pdf":
        text = _pdf_text(content)
    elif ext == "docx":
        text = _docx_text(content)
    else:
        text = _pptx_text(content)
    return text.strip()[:MAX_CHARS], "text"
