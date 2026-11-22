"""Malware scanning. Fails closed: if no scanner answers, the file is NOT marked clean."""
import logging
import socket
import struct
from dataclasses import dataclass

from django.conf import settings
from django.utils.module_loading import import_string

from .models import Resource

log = logging.getLogger(__name__)


@dataclass
class ScanResult:
    status: str  # Resource.ScanStatus value
    detail: str = ""


class ClamAVScanner:
    """Talks to a clamd daemon using the INSTREAM protocol (no extra Python package)."""

    CHUNK = 8192

    def __init__(self, host=None, port=None, unix_socket=None, timeout=None):
        self.host = host if host is not None else settings.CLAMAV_HOST
        self.port = port or settings.CLAMAV_PORT
        self.unix_socket = unix_socket if unix_socket is not None else settings.CLAMAV_UNIX_SOCKET
        self.timeout = timeout or settings.CLAMAV_TIMEOUT

    def _connect(self):
        if self.unix_socket:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            s.connect(self.unix_socket)
            return s
        if not self.host:
            raise ConnectionError("ClamAV is not configured")
        return socket.create_connection((self.host, self.port), timeout=self.timeout)

    def scan(self, fileobj):
        try:
            with self._connect() as s:
                s.sendall(b"zINSTREAM\0")
                fileobj.seek(0)
                for chunk in iter(lambda: fileobj.read(self.CHUNK), b""):
                    s.sendall(struct.pack("!I", len(chunk)) + chunk)
                s.sendall(struct.pack("!I", 0))
                reply = b""
                while not reply.endswith(b"\0") and len(reply) < 4096:
                    part = s.recv(1024)
                    if not part:
                        break
                    reply += part
        except (OSError, ConnectionError) as exc:
            log.warning("ClamAV unavailable: %s", exc)
            return ScanResult(Resource.ScanStatus.UNAVAILABLE, "Scanner could not be reached")
        finally:
            fileobj.seek(0)

        text = reply.rstrip(b"\0\n").decode("utf-8", "replace")
        if text.endswith("OK"):
            return ScanResult(Resource.ScanStatus.CLEAN, "No threats found")
        if text.endswith("FOUND"):
            return ScanResult(Resource.ScanStatus.INFECTED, text.split(":", 1)[-1].strip()[:200])
        log.warning("Unexpected ClamAV reply: %r", text)
        return ScanResult(Resource.ScanStatus.UNAVAILABLE, "Scanner returned an error")


def get_scanner():
    path = settings.RESOURCE_SCANNER
    return import_string(path)() if path else None


def scan_resource(resource):
    """Scan the stored file and save the outcome. Safe to call repeatedly."""
    scanner = get_scanner()
    if scanner is None:
        result = ScanResult(Resource.ScanStatus.UNAVAILABLE, "No scanner is configured")
    else:
        with resource.file.open("rb") as fh:
            result = scanner.scan(fh)
    resource.scan_status = result.status
    resource.scan_detail = result.detail
    resource.save(update_fields=["scan_status", "scan_detail"])
    return result
