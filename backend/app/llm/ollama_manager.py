"""
Ollama process manager for Regia.
Auto-starts and monitors the Ollama server when Regia starts.
"""

import subprocess
import shutil
import logging
import time
import platform
from typing import Optional

import httpx

logger = logging.getLogger("regia.ollama_manager")


class OllamaManager:
    """Manages the Ollama process lifecycle."""

    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "qwen2.5:0.5b"):
        self.base_url = base_url
        self.model_name = model_name
        self._process: Optional[subprocess.Popen] = None

    def is_installed(self) -> bool:
        """Check if Ollama is installed on the system."""
        return shutil.which("ollama") is not None

    async def is_running(self) -> bool:
        """Check if Ollama server is already running."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/api/tags", timeout=3)
                return resp.status_code == 200
        except Exception:
            return False

    def start(self) -> bool:
        """Start the Ollama server process."""
        if not self.is_installed():
            logger.warning("Ollama is not installed — AI features will use rule-based fallback")
            return False

        try:
            system = platform.system()
            if system == "Windows":
                # On Windows, start Ollama serve in background
                self._process = subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                self._process = subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            # Wait for server to be ready
            for _ in range(15):
                time.sleep(1)
                try:
                    resp = httpx.get(f"{self.base_url}/api/tags", timeout=2)
                    if resp.status_code == 200:
                        logger.info("Ollama server started successfully")
                        return True
                except Exception:
                    continue

            logger.warning("Ollama server started but not responding yet")
            return True

        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")
            return False

    async def ensure_model(self) -> bool:
        """Ensure the configured model is available, pull if needed."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/api/tags", timeout=5)
                if resp.status_code != 200:
                    return False

                models = resp.json().get("models", [])
                model_names = [m.get("name", "") for m in models]

                if self.model_name in model_names:
                    logger.info(f"Model '{self.model_name}' is available")
                    return True

                # Pull the model
                logger.info(f"Pulling model '{self.model_name}'...")
                resp = await client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": self.model_name},
                    timeout=600,  # 10 minutes for download
                )
                return resp.status_code == 200

        except Exception as e:
            logger.error(f"Failed to ensure model: {e}")
            return False

    def stop(self):
        """Stop the Ollama server process if we started it."""
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=10)
                logger.info("Ollama server stopped")
            except Exception as e:
                logger.warning(f"Error stopping Ollama: {e}")
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None

    @property
    def managed(self) -> bool:
        """Whether we are managing the Ollama process."""
        return self._process is not None
