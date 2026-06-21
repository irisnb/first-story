"""LLM Configuration Service.

Manages LLM configs per project with simple encryption for API keys.
"""

import base64
import json
import logging
from pathlib import Path
from typing import Optional

from ..config import get_settings
from ..models.llm_config import (
    LLMConfig,
    LLMConfigResponse,
    LLMConfigSlot,
    LLMConfigUpdateRequest,
)

logger = logging.getLogger("first_story.llm_config")


def _encode_key(api_key: str, project_id: str) -> str:
    """Simple encoding: base64(api_key:project_id).
    
    This is NOT cryptographic encryption, just obfuscation to prevent
    accidental exposure. V2 can upgrade to proper encryption.
    """
    if not api_key:
        return ""
    combined = f"{api_key}:{project_id}"
    return base64.b64encode(combined.encode()).decode()


def _decode_key(encoded: str, project_id: str) -> str:
    """Decode the API key."""
    if not encoded:
        return ""
    try:
        combined = base64.b64decode(encoded.encode()).decode()
        parts = combined.split(":")
        if len(parts) >= 2 and parts[-1] == project_id:
            return ":".join(parts[:-1])
        # Legacy: no project_id in encoding
        return combined
    except Exception:
        return ""


def _mask_key(api_key: str) -> str:
    """Mask API key, showing only last 4 chars."""
    if not api_key or len(api_key) < 4:
        return "****"
    return f"****{api_key[-4:]}"


class LLMConfigService:
    """Service for managing LLM configurations."""

    def __init__(self, project_dir: Path, project_id: str):
        """Initialize the service.
        
        Args:
            project_dir: Path to the project directory
            project_id: Project ID (used for key encoding)
        """
        self.project_dir = project_dir
        self.project_id = project_id
        self.config_file = project_dir / "llm_config.json"

    def _load_raw(self) -> dict:
        """Load raw config from file."""
        if not self.config_file.exists():
            return {}
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to load LLM config: %s", e)
            return {}

    def _save_raw(self, data: dict) -> None:
        """Save raw config to file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_config(self, slot: LLMConfigSlot) -> LLMConfig:
        """Get config for a slot, with fallback to environment variables.
        
        Args:
            slot: Configuration slot (chat or utility)
            
        Returns:
            LLMConfig, either from file or environment variables
        """
        raw = self._load_raw()
        slot_data = raw.get(slot, {})
        
        # Check if explicitly configured
        if slot_data.get("api_key"):
            return LLMConfig(
                slot=slot,
                provider=slot_data.get("provider", "deepseek"),
                model=slot_data.get("model", "deepseek-chat"),
                api_endpoint=slot_data.get("api_endpoint", "https://api.deepseek.com"),
                api_key=_decode_key(slot_data.get("api_key", ""), self.project_id),
                proxy=slot_data.get("proxy", ""),
                timeout_seconds=slot_data.get("timeout_seconds", 60.0),
                is_configured=True,
            )
        
        # Fallback to environment variables
        settings = get_settings()
        return LLMConfig(
            slot=slot,
            provider=settings.llm_provider,
            model=settings.llm_model,
            api_endpoint=settings.llm_base_url,
            api_key=settings.llm_api_key,
            proxy=settings.llm_proxy,
            timeout_seconds=settings.llm_timeout_seconds,
            is_configured=False,
        )

    def get_config_response(self, slot: LLMConfigSlot) -> LLMConfigResponse:
        """Get config for API response (masked key)."""
        config = self.get_config(slot)
        return LLMConfigResponse(
            slot=config.slot,
            provider=config.provider,
            model=config.model,
            api_endpoint=config.api_endpoint,
            api_key_preview=_mask_key(config.api_key),
            proxy=config.proxy,
            timeout_seconds=config.timeout_seconds,
            is_configured=config.is_configured,
        )

    def get_all_configs(self) -> list[LLMConfigResponse]:
        """Get all configs."""
        return [
            self.get_config_response("chat"),
            self.get_config_response("utility"),
        ]

    def update_config(
        self,
        slot: LLMConfigSlot,
        update: LLMConfigUpdateRequest,
    ) -> LLMConfig:
        """Update config for a slot.
        
        Args:
            slot: Configuration slot
            update: Update request
            
        Returns:
            Updated config
        """
        raw = self._load_raw()
        
        # Get existing or create new
        slot_data = raw.get(slot, {})
        
        # Update fields
        if update.provider is not None:
            slot_data["provider"] = update.provider
        if update.model is not None:
            slot_data["model"] = update.model
        if update.api_endpoint is not None:
            slot_data["api_endpoint"] = update.api_endpoint
        if update.api_key is not None:
            slot_data["api_key"] = _encode_key(update.api_key, self.project_id)
        if update.proxy is not None:
            slot_data["proxy"] = update.proxy
        if update.timeout_seconds is not None:
            slot_data["timeout_seconds"] = update.timeout_seconds
        
        # Save
        raw[slot] = slot_data
        self._save_raw(raw)
        
        return self.get_config(slot)

    def delete_config(self, slot: LLMConfigSlot) -> None:
        """Delete config for a slot (revert to environment variables)."""
        raw = self._load_raw()
        if slot in raw:
            del raw[slot]
            self._save_raw(raw)

    def init_config_file(self) -> None:
        """Initialize empty config file."""
        if not self.config_file.exists():
            self._save_raw({})
