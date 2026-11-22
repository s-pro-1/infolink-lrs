"""Private file storage.

Today: a folder on disk outside MEDIA_ROOT. At deployment, make
`get_private_storage` return an S3-compatible storage (Cloudflare R2) with a
private bucket; nothing else in the app needs to change.
"""
import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateFileSystemStorage(FileSystemStorage):
    """Reads its folder from settings on every use (so tests can redirect it)
    and refuses to produce public URLs."""

    @property
    def base_location(self):
        return str(settings.PRIVATE_MEDIA_ROOT)

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    @property
    def base_url(self):
        raise ValueError("Private files have no public URL; serve them through the download view.")


_storage = PrivateFileSystemStorage()


def get_private_storage():
    return _storage
