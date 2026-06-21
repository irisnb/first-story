"""Tests for LLM Configuration Service."""

import json
import tempfile
from pathlib import Path

import pytest

from app.models.llm_config import LLMConfig, LLMConfigResponse, LLMConfigSlot
from app.services.llm_config import (
    LLMConfigService,
    _encode_key,
    _decode_key,
    _mask_key,
)


class TestKeyEncoding:
    """Test the simple encoding/decoding functions."""

    def test_encode_decode_roundtrip(self):
        """Test that encoding and decoding returns the original key."""
        api_key = "sk-test-12345678"
        project_id = "proj_20260101_abc123"
        
        encoded = _encode_key(api_key, project_id)
        decoded = _decode_key(encoded, project_id)
        
        assert decoded == api_key

    def test_encode_empty_key(self):
        """Test encoding an empty key."""
        assert _encode_key("", "proj_123") == ""

    def test_decode_empty_key(self):
        """Test decoding an empty key."""
        assert _decode_key("", "proj_123") == ""

    def test_decode_invalid_key(self):
        """Test decoding an invalid key returns empty."""
        assert _decode_key("not-valid-base64!!!", "proj_123") == ""

    def test_decode_wrong_project_id(self):
        """Test decoding with wrong project ID."""
        api_key = "sk-test-12345678"
        project_id = "proj_20260101_abc123"
        
        encoded = _encode_key(api_key, project_id)
        # Decoding with different project ID should still work (legacy mode)
        decoded = _decode_key(encoded, "proj_different")
        # The key is returned because the format is "key:project_id"
        # and we check if the suffix matches
        assert decoded != api_key  # Should fail validation


class TestKeyMasking:
    """Test the key masking function."""

    def test_mask_key_normal(self):
        """Test masking a normal key."""
        assert _mask_key("sk-1234567890abcd") == "****abcd"

    def test_mask_key_short(self):
        """Test masking a short key."""
        assert _mask_key("ab") == "****"

    def test_mask_key_empty(self):
        """Test masking an empty key."""
        assert _mask_key("") == "****"

    def test_mask_key_exact_four(self):
        """Test masking a key with exactly 4 chars."""
        assert _mask_key("abcd") == "****abcd"


class TestLLMConfigService:
    """Test the LLMConfigService class."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_init_config_file(self, temp_project_dir):
        """Test initializing the config file."""
        service = LLMConfigService(temp_project_dir, "proj_test")
        service.init_config_file()
        
        config_file = temp_project_dir / "llm_config.json"
        assert config_file.exists()
        
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data == {}

    def test_get_config_env_fallback(self, temp_project_dir, monkeypatch):
        """Test getting config falls back to environment variables."""
        monkeypatch.setenv("FIRST_STORY_LLM_API_KEY", "sk-env-key-1234")
        monkeypatch.setenv("FIRST_STORY_LLM_PROVIDER", "openai")
        monkeypatch.setenv("FIRST_STORY_LLM_MODEL", "gpt-4")
        
        service = LLMConfigService(temp_project_dir, "proj_test")
        config = service.get_config("chat")
        
        assert config.is_configured is False
        assert config.api_key == "sk-env-key-1234"
        assert config.provider == "openai"
        assert config.model == "gpt-4"

    def test_update_config(self, temp_project_dir):
        """Test updating config for a slot."""
        from app.models.llm_config import LLMConfigUpdateRequest
        
        service = LLMConfigService(temp_project_dir, "proj_test")
        
        update = LLMConfigUpdateRequest(
            provider="deepseek",
            model="deepseek-chat",
            api_key="sk-test-12345678",
            api_endpoint="https://api.deepseek.com",
        )
        
        result = service.update_config("chat", update)
        
        assert result.is_configured is True
        assert result.provider == "deepseek"
        assert result.model == "deepseek-chat"
        assert result.api_key == "sk-test-12345678"

    def test_get_config_response_masks_key(self, temp_project_dir):
        """Test that get_config_response masks the API key."""
        from app.models.llm_config import LLMConfigUpdateRequest
        
        service = LLMConfigService(temp_project_dir, "proj_test")
        
        update = LLMConfigUpdateRequest(api_key="sk-test-12345678")
        service.update_config("utility", update)
        
        response = service.get_config_response("utility")
        
        assert response.api_key_preview == "****5678"
        assert response.is_configured is True

    def test_delete_config(self, temp_project_dir):
        """Test deleting config for a slot."""
        from app.models.llm_config import LLMConfigUpdateRequest
        
        service = LLMConfigService(temp_project_dir, "proj_test")
        
        # Set a config
        update = LLMConfigUpdateRequest(api_key="sk-test-1234")
        service.update_config("chat", update)
        
        # Delete it
        service.delete_config("chat")
        
        # Verify it's gone
        config = service.get_config("chat")
        assert config.is_configured is False

    def test_separate_slot_configs(self, temp_project_dir):
        """Test that chat and utility slots have separate configs."""
        from app.models.llm_config import LLMConfigUpdateRequest
        
        service = LLMConfigService(temp_project_dir, "proj_test")
        
        # Set different configs for each slot
        service.update_config("chat", LLMConfigUpdateRequest(
            provider="openai",
            model="gpt-4",
            api_key="sk-chat-key-1234",
        ))
        service.update_config("utility", LLMConfigUpdateRequest(
            provider="deepseek",
            model="deepseek-chat",
            api_key="sk-utility-key-5678",
        ))
        
        chat_config = service.get_config("chat")
        utility_config = service.get_config("utility")
        
        assert chat_config.provider == "openai"
        assert chat_config.model == "gpt-4"
        assert chat_config.api_key == "sk-chat-key-1234"
        
        assert utility_config.provider == "deepseek"
        assert utility_config.model == "deepseek-chat"
        assert utility_config.api_key == "sk-utility-key-5678"

    def test_all_configs(self, temp_project_dir):
        """Test getting all configs."""
        service = LLMConfigService(temp_project_dir, "proj_test")
        
        configs = service.get_all_configs()
        
        assert len(configs) == 2
        slot_names = {c.slot for c in configs}
        assert slot_names == {"chat", "utility"}
