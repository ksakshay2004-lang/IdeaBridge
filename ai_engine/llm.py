"""LLM provider abstraction. Add a provider by subclassing LLMProvider and registering it in get_llm()."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional


class LLMError(RuntimeError):
    pass


def _post_json(url: str, headers: dict, payload: dict, timeout: int = 120) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:  # never include headers/keys in the message
        raise LLMError(f"LLM API returned HTTP {e.code}") from None
    except Exception as e:
        raise LLMError(f"LLM request failed: {type(e).__name__}") from None


class LLMProvider:
    name = "base"
    model = ""

    def complete_json(self, system: str, user: str, max_tokens: int = 3500) -> str:  # pragma: no cover
        """Return the raw text of a JSON-only completion."""
        raise NotImplementedError


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-5-5"):
        self.api_key, self.model = api_key, model

    def complete_json(self, system: str, user: str, max_tokens: int = 3500) -> str:
        data = _post_json("https://api.anthropic.com/v1/messages",
                          {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                          {"model": self.model, "max_tokens": max_tokens, "system": system,
                           "messages": [{"role": "user", "content": user}]})
        parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
        text = "".join(parts).strip()
        if not text:
            raise LLMError("Empty response from Anthropic API")
        return text


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str = "https://api.openai.com/v1"):
        self.api_key, self.model, self.base_url = api_key, model, base_url.rstrip("/")

    def complete_json(self, system: str, user: str, max_tokens: int = 3500) -> str:
        data = _post_json(self.base_url + "/chat/completions", {"Authorization": f"Bearer {self.api_key}"},
                          {"model": self.model, "max_tokens": max_tokens,
                           "response_format": {"type": "json_object"},
                           "messages": [{"role": "system", "content": system},
                                        {"role": "user", "content": user}]})
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError):
            raise LLMError("Unexpected response shape from OpenAI API") from None


def get_llm(provider: str = "none", model: str = "", anthropic_key: str = "", openai_key: str = "",
            openai_base_url: str = "https://api.openai.com/v1") -> Optional[LLMProvider]:
    """Return a live provider, or None (=> DEMO MODE) when none is configured with a key."""
    provider = (provider or "none").lower()
    if provider == "anthropic" and anthropic_key:
        return AnthropicProvider(anthropic_key, model or "claude-sonnet-5-5")
    if provider == "openai" and openai_key:
        return OpenAIProvider(openai_key, model or "gpt-4o-mini", openai_base_url)
    return None
