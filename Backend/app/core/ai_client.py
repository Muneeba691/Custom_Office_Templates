from app.core.config import get_settings

settings = get_settings()


class AINotConfiguredError(Exception):
    """Raised when an AI operation is attempted without credentials configured."""


class AIClient:
    def __init__(self) -> None:
        self._configured = bool(settings.AI_PROVIDER_API_KEY)

    @property
    def is_configured(self) -> bool:
        return self._configured

    @property
    def model(self) -> str:
        return settings.AI_MODEL_DEFAULT or "not-configured"

    def _require_configured(self) -> None:
        if not self._configured:
            raise AINotConfiguredError(
                "AI provider is NOT CONFIGURED. Set AI_PROVIDER_API_KEY in .env."
            )

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        self._require_configured()
        raise NotImplementedError("AI provider client wiring pending real credentials")


def get_ai_client() -> AIClient:
    return AIClient()
