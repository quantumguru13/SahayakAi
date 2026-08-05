"""Application configuration via pydantic-settings.

DEMO_MODE is auto-enabled when no OpenAI key is present, so the entire
platform runs — flawlessly — for a judge demo with zero external credentials.
Provide OPENAI_API_KEY (and optionally Supabase creds) to switch to live AI.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    app_name: str = "Sahayak AI"
    api_v1_prefix: str = "/api/v1"
    # The deployed frontend (Firebase Hosting) calls this API cross-origin, so
    # both Hosting domains ship as defaults. Override with CORS_ORIGINS.
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "https://sahayakai-f45db.web.app,https://sahayakai-f45db.firebaseapp.com"
    )

    # --- OpenAI ---
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_temperature: float = 0.1

    # --- Supabase ---
    supabase_url: str = ""
    supabase_service_key: str = ""  # new format: the "sb_secret_..." key
    supabase_jwt_secret: str = ""   # legacy shared-secret (HS256) verification
    supabase_jwks_url: str = ""     # modern asymmetric (ES256/RS256) verification
    supabase_jwt_aud: str = "authenticated"
    # Single-tenant org id all persisted rows are scoped to (PRD: single-org tenant).
    default_org_id: str = "default-org"

    # --- Behaviour ---
    force_demo_mode: bool = False
    # Force-disable auth even when Supabase is configured (guaranteed offline demo)
    force_disable_auth: bool = False
    # Dynamic runtime flag set if OpenAI authentication or connection fails
    openai_auth_failed: bool = False
    # OCR tuning (LIVE mode). Point this at tesseract.exe on Windows if not on PATH.
    tesseract_cmd: str = ""
    # Audit mode retains the uploaded imagery in the pipeline-debug payload. OFF by
    # default: an Aadhaar photo is the document itself, so it is discarded once the
    # fields have been read (AUDIT_MODE=true re-enables it for pipeline inspection).
    audit_mode: bool = False
    # The LIVE pipeline is offline-first: Tesseract -> EasyOCR for OCR, and the
    # deterministic rule extractor for structured fields. OpenAI (GPT-4o vision +
    # JSON extraction) is opt-in only via USE_OPENAI=true, so a key left in the
    # environment never silently makes document intake depend on the network.
    use_openai: bool = False

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key.strip()) and not self.openai_auth_failed

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url.strip() and self.supabase_service_key.strip())

    @property
    def demo_mode(self) -> bool:
        """Legacy flag: true when GPT-4o is unavailable.

        NOTE: this no longer decides the document pipeline — the client picks LIVE
        or DEMO per upload (see routes/documents.py). It still gates OpenAI-only
        features (real embeddings), which safely fall back to deterministic vectors.
        """
        return self.force_demo_mode or not self.openai_configured

    def live_ocr_engines(self) -> list[str]:
        """OCR engines usable for real (LIVE) document reading, in preference order.

        Offline engines come first and OpenAI is excluded unless explicitly opted
        into — LIVE mode must work with no network and no API key.
        """
        from app.core.ocr import available_engines

        return available_engines(
            include_openai=self.use_openai and self.openai_configured
        )

    @property
    def live_ocr_available(self) -> bool:
        """True when a real document can actually be transcribed (local OCR or GPT-4o)."""
        return bool(self.live_ocr_engines())

    @property
    def default_pipeline_mode(self) -> str:
        """LIVE when we can genuinely read documents; otherwise DEMO. FORCE_DEMO_MODE
        always wins so an offline stage demo is guaranteed to work."""
        if self.force_demo_mode:
            return "DEMO"
        return "LIVE" if self.live_ocr_available else "DEMO"

    @property
    def jwks_url(self) -> str:
        """Explicit JWKS URL, or derive it from the Supabase project URL."""
        if self.supabase_jwks_url.strip():
            return self.supabase_jwks_url.strip()
        if self.supabase_url.strip():
            return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        return ""

    @property
    def auth_enabled(self) -> bool:
        """Enforce JWT auth only once a Supabase project is configured. In a pure
        offline demo (no Supabase, or FORCE_DISABLE_AUTH) auth is bypassed."""
        if self.force_disable_auth or self.force_demo_mode:
            return False
        return bool(self.supabase_url.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
