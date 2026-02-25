"""
Ollama client for Regia.
Provides async interface to local Ollama LLM server.
Designed to work with ultra-lightweight models (Qwen2.5:0.5b, TinyLlama, Phi-2).
"""

import logging
from typing import Optional, Dict, Any, AsyncGenerator

import httpx

from app.config import LLMConfig

logger = logging.getLogger("regia.llm.ollama")


class OllamaClient:
    """Async client for Ollama API."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.ollama_base_url.rstrip("/")
        self._available: Optional[bool] = None

    async def is_available(self) -> bool:
        """Check if Ollama server is running and the model is available."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    self._available = any(
                        self.config.model_name in name for name in model_names
                    )
                    if not self._available:
                        logger.warning(
                            f"Model '{self.config.model_name}' not found. "
                            f"Available: {model_names}"
                        )
                    return self._available
        except Exception as e:
            logger.debug(f"Ollama not available: {e}")
            self._available = False
        return False

    async def generate(self, prompt: str, system: str = "") -> str:
        """
        Generate a response from the LLM.
        Returns the generated text, or empty string on failure.
        """
        try:
            payload = {
                "model": self.config.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                },
            }
            if system:
                payload["system"] = system

            async with httpx.AsyncClient(
                timeout=self.config.timeout_seconds
            ) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
                result = resp.json()
                return result.get("response", "").strip()

        except httpx.TimeoutException:
            logger.warning("Ollama request timed out")
            return ""
        except Exception as e:
            logger.error(f"Ollama generate failed: {e}")
            return ""

    async def generate_stream(
        self, prompt: str, system: str = ""
    ) -> AsyncGenerator[str, None]:
        """Stream a response from the LLM token by token."""
        try:
            payload = {
                "model": self.config.model_name,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                },
            }
            if system:
                payload["system"] = system

            async with httpx.AsyncClient(
                timeout=self.config.timeout_seconds
            ) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json=payload,
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line:
                            import json
                            try:
                                data = json.loads(line)
                                token = data.get("response", "")
                                if token:
                                    yield token
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"Ollama stream failed: {e}")

    async def chat(self, messages: list, system: str = "") -> str:
        """
        Chat-style completion using Ollama's chat API.
        messages: list of {"role": "user"|"assistant", "content": "..."}
        """
        try:
            chat_messages = []
            if system:
                chat_messages.append({"role": "system", "content": system})
            chat_messages.extend(messages)

            payload = {
                "model": self.config.model_name,
                "messages": chat_messages,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                },
            }

            async with httpx.AsyncClient(
                timeout=self.config.timeout_seconds
            ) as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                resp.raise_for_status()
                result = resp.json()
                return result.get("message", {}).get("content", "").strip()

        except Exception as e:
            logger.error(f"Ollama chat failed: {e}")
            return ""

    async def pull_model(self, model_name: Optional[str] = None) -> bool:
        """Pull/download a model from Ollama registry."""
        model = model_name or self.config.model_name
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model, "stream": False},
                )
                resp.raise_for_status()
                logger.info(f"Model '{model}' pulled successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to pull model '{model}': {e}")
            return False

    async def list_models(self) -> list:
        """List available models on the Ollama server."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                return resp.json().get("models", [])
        except Exception:
            return []
