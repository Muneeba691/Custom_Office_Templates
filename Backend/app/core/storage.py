from app.core.config import get_settings

settings = get_settings()


class StorageNotConfiguredError(Exception):
    """Raised when a storage operation is attempted without credentials configured."""


class ObjectStorage:
    def __init__(self) -> None:
        self._configured = all(
            [
                settings.STORAGE_ENDPOINT,
                settings.STORAGE_ACCESS_KEY,
                settings.STORAGE_SECRET_KEY,
                settings.STORAGE_BUCKET,
            ]
        )

    @property
    def is_configured(self) -> bool:
        return self._configured

    def _require_configured(self) -> None:
        if not self._configured:
            raise StorageNotConfiguredError(
                "Object storage is NOT CONFIGURED. Set STORAGE_ENDPOINT, "
                "STORAGE_ACCESS_KEY, STORAGE_SECRET_KEY, STORAGE_BUCKET in .env."
            )

    def generate_upload_url(self, key: str, content_type: str, expires_seconds: int = 300) -> str:
        self._require_configured()
        raise NotImplementedError("S3 client wiring pending real credentials")

    def generate_download_url(self, key: str, expires_seconds: int = 300) -> str:
        self._require_configured()
        raise NotImplementedError("S3 client wiring pending real credentials")

    def delete_object(self, key: str) -> None:
        self._require_configured()
        raise NotImplementedError("S3 client wiring pending real credentials")


def get_storage() -> ObjectStorage:
    return ObjectStorage()
