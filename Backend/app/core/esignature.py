from app.core.config import get_settings

settings = get_settings()


class ESignatureNotConfiguredError(Exception):
    """Raised when an e-signature operation is attempted without credentials configured."""


class ESignatureProvider:
    def __init__(self) -> None:
        self._configured = all(
            [
                settings.ESIGNATURE_API_KEY,
                settings.ESIGNATURE_API_URL,
            ]
        )

    @property
    def is_configured(self) -> bool:
        return self._configured

    def _require_configured(self) -> None:
        if not self._configured:
            raise ESignatureNotConfiguredError(
                "E-signature provider is NOT CONFIGURED. Set ESIGNATURE_API_KEY, "
                "ESIGNATURE_API_URL in .env."
            )

    def send_for_signature(self, document_key: str, signer_email: str, signer_name: str) -> str:
        self._require_configured()
        raise NotImplementedError("E-signature client wiring pending real credentials")

    def check_signature_status(self, envelope_id: str) -> str:
        self._require_configured()
        raise NotImplementedError("E-signature client wiring pending real credentials")

    def download_signed_document(self, envelope_id: str) -> bytes:
        self._require_configured()
        raise NotImplementedError("E-signature client wiring pending real credentials")


def get_esignature_provider() -> ESignatureProvider:
    return ESignatureProvider()
