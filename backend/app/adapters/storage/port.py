from typing import Protocol


class ObjectStoragePort(Protocol):
    def create_upload_url(self, *, key: str, content_type: str, expires_seconds: int = 900) -> str: ...

    def create_download_url(self, *, key: str, expires_seconds: int = 900) -> str: ...
