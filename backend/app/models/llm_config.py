"""LLM Configuration models.

Two slots: chat (main dialogue) and utility (classification, summary, etc.)
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


LLMConfigSlot = Literal["chat", "utility"]

# Supported providers
LLMProvider = Literal["deepseek", "openai", "anthropic", "local"]


class LLMConfig(BaseModel):
    """LLM configuration for a single slot."""

    slot: LLMConfigSlot = Field(..., description="Configuration slot: chat or utility")
    provider: LLMProvider = Field(default="deepseek", description="LLM provider name")
    model: str = Field(default="deepseek-chat", description="Model identifier")
    api_endpoint: str = Field(
        default="https://api.deepseek.com",
        description="API endpoint URL"
    )
    api_key: str = Field(default="", description="API key (encrypted in storage)")
    proxy: str = Field(default="", description="Proxy URL for API calls")
    timeout_seconds: float = Field(default=60.0, description="Request timeout")

    # Whether this config is set (vs using env fallback)
    is_configured: bool = Field(
        default=False,
        description="True if explicitly configured, False if using env fallback"
    )


class LLMConfigResponse(BaseModel):
    """API response for LLM config (API key masked)."""

    slot: LLMConfigSlot
    provider: LLMProvider
    model: str
    api_endpoint: str
    api_key_preview: str = Field(
        default="",
        description="Last 4 chars of API key, prefixed with ****"
    )
    proxy: str
    timeout_seconds: float
    is_configured: bool


class LLMConfigUpdateRequest(BaseModel):
    """Request to update LLM config."""

    provider: Optional[LLMProvider] = None
    model: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    proxy: Optional[str] = None
    timeout_seconds: Optional[float] = None


class LLMConfigListResponse(BaseModel):
    """Response listing all LLM configs."""

    configs: list[LLMConfigResponse]
