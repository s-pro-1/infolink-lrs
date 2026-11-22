"""Upload validation. Every check looks at the file's actual bytes, not just
its name or the browser-supplied content type.

Limits worth knowing (also written up in docs/ASSUMPTIONS.md):
- Legacy .doc/.ppt share one signature (OLE) and can carry macros. We accept them
  because students still use them, but they rely on the scanner and on the human
  moderator.
- This does not detect inappropriate content. That is what moderation is for.
"""
import hashlib
import io
import re
import zipfile
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError

OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

ALLOWED = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "txt": "text/plain",
}
ALLOWED_LABEL = "PDF, DOC, DOCX, PPT, PPTX or TXT"

MAX_ZIP_ENTRIES = 5000
MAX_UNCOMPRESSED_BYTES = 300 * 1024 * 1024
HTML_START = re.compile(rb"^\s*(<!doctype\s+html|<html|<script|<\?php|#!)", re.I)


@dataclass
class ValidatedFile:
    extension: str
    mime_type: str
    size: int
    sha256: str
    safe_name: str


def safe_display_name(name):
    """Keep a readable, harmless version of the original name for display and download."""
    base = name.replace("\\", "/").rsplit("/", 1)[-1]
    base = re.sub(r"[^\w.\- ]", "_", base, flags=re.UNICODE).strip(" .")
    return (base or "file")[:150]


def _read_head(f, n):
    f.seek(0)
    data = f.read(n)
    f.seek(0)
    return data


def _check_ooxml(f, kind):
    f.seek(0)
    try:
        zf = zipfile.ZipFile(f)
        infos = zf.infolist()
    except zipfile.BadZipFile:
        raise ValidationError("This file looks damaged. Open it on your computer and save it again.")
    if len(infos) > MAX_ZIP_ENTRIES or sum(i.file_size for i in infos) > MAX_UNCOMPRESSED_BYTES:
        raise ValidationError("This file is unusually large when unpacked, so it was not accepted.")
    names = [i.filename for i in infos]
    if any(n.startswith(("/", "..")) or "/../" in n for n in names):
        raise ValidationError("This file contains unsafe internal paths and was not accepted.")
    if "[Content_Types].xml" not in names or not any(n.startswith(f"{kind}/") for n in names):
        raise ValidationError("The file does not match its type. Save it as a real Office document and try again.")
    if any(n.lower().endswith(("vbaproject.bin", ".exe", ".dll", ".js", ".vbs")) for n in names):
        raise ValidationError("Documents containing macros or programs are not accepted.")
    f.seek(0)


def _check_txt(f):
    head = _read_head(f, 65536)
    if b"\x00" in head:
        raise ValidationError("This does not look like a plain text file.")
    if HTML_START.match(head[:1024]):
        raise ValidationError("Web pages and scripts are not accepted. Upload a PDF or Office document instead.")
    controls = sum(1 for b in head if b < 9 or 13 < b < 32)
    if head and controls / len(head) > 0.01:
        raise ValidationError("This does not look like a plain text file.")


def validate_upload(uploaded):
    """Return ValidatedFile or raise ValidationError with a user-friendly message."""
    name = getattr(uploaded, "name", "") or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED:
        raise ValidationError(f"Only {ALLOWED_LABEL} files can be uploaded.")

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if uploaded.size > max_bytes:
        raise ValidationError(f"This file is {uploaded.size / 1048576:.1f} MB. The limit is {settings.MAX_UPLOAD_MB} MB.")
    if uploaded.size == 0:
        raise ValidationError("This file is empty.")

    head = _read_head(uploaded, 16)
    mismatch = ValidationError("The file's contents do not match its type. Check that it is a real {} file.".format(ext.upper()))
    if ext == "pdf":
        if not head.startswith(b"%PDF-"):
            raise mismatch
    elif ext in ("doc", "ppt"):
        if not head.startswith(OLE_MAGIC):
            raise mismatch
    elif ext in ("docx", "pptx"):
        if not head.startswith(b"PK\x03\x04"):
            raise mismatch
        _check_ooxml(uploaded, "word" if ext == "docx" else "ppt")
    elif ext == "txt":
        _check_txt(uploaded)

    digest = hashlib.sha256()
    uploaded.seek(0)
    for chunk in iter(lambda: uploaded.read(1024 * 1024), b""):
        digest.update(chunk)
    uploaded.seek(0)
    return ValidatedFile(ext, ALLOWED[ext], uploaded.size, digest.hexdigest(), safe_display_name(name))
