"""LLM Router V2 - Phase 2 - Multi-tier with Ollama local + optional cloud"""
import os
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("RouterV2")

@dataclass
class LLMResponse:
    text: str
    tier: str
    model: str
    latency_ms: int = 0
    from_cache: bool = False

class LLMRouter:
    """Multi-tier LLM routing - Phase 2 with Ollama local"""

    def __init__(self, default_provider: str = "ollama"):
        self.provider = default_provider
        self.tiers = {
            "fast": {
                "description": "Quick lookups, time, open commands",
                "models": {
                    "ollama": "llama3.1:8b",
                    "openai": "gpt-4o-mini",
                    "anthropic": "claude-3-haiku",
                    "local": "llama3.1:8b"
                },
                "max_tokens": 100,
                "temperature": 0.3
            },
            "brain": {
                "description": "Conversation, how/what questions",
                "models": {
                    "ollama": "llama3.1:8b",
                    "openai": "gpt-4o",
                    "anthropic": "claude-3-sonnet",
                    "local": "llama3.1:8b"
                },
                "max_tokens": 300,
                "temperature": 0.7
            },
            "deep": {
                "description": "Complex reasoning, planning",
                "models": {
                    "ollama": "deepseek-r1:8b",
                    "openai": "gpt-4o",
                    "anthropic": "claude-3-opus",
                    "local": "llama3.1:70b"
                },
                "max_tokens": 1000,
                "temperature": 0.8
            },
            "local": {
                "description": "Offline fallback",
                "models": {
                    "ollama": "llama3.1:8b",
                    "local": "llama3.1:8b"
                },
                "max_tokens": 300,
                "temperature": 0.7
            }
        }

        self.ollama_available = False
        self.ollama_client = None
        self._init_ollama()

        logger.info(f"LLM Router V2 - Provider: {self.provider}, Ollama: {self.ollama_available}, Tiers: {list(self.tiers.keys())}")

    def _init_ollama(self):
        try:
            import ollama
            # Test if Ollama server is running
            try:
                client = ollama.Client()
                models = client.list()
                self.ollama_available = True
                self.ollama_client = client
                logger.info(f"Ollama available, models: {[m['name'] for m in models.get('models', [])][:3]}")
            except Exception as e:
                logger.warning(f"Ollama server not running or no models: {e} - will use mock")
                self.ollama_available = False
        except ImportError:
            logger.warning("ollama package not installed - pip install ollama - using mock")
            self.ollama_available = False
        except Exception as e:
            logger.warning(f"Ollama init failed: {e}")
            self.ollama_available = False

    def route(self, text: str) -> str:
        """Route text to appropriate tier"""
        lower = text.lower()
        length = len(lower)

        # Fast tier: short commands, quick lookups
        if length < 20 or any(kw in lower for kw in ["time", "open", "close", "what time", "help", "status"]):
            return "fast"
        # Deep tier: complex planning
        elif any(kw in lower for kw in ["plan my", "complex", "analyze", "research", "weekend", "project"]) or length > 150:
            return "deep"
        # Brain tier: conversational
        elif any(kw in lower for kw in ["how", "what", "why", "explain", "who", "when"]) or length < 100:
            return "brain"
        else:
            return "local"

    async def generate(self, prompt: str, tier: str = "auto", system_prompt: str = None) -> LLMResponse:
        import time
        start = time.time()

        if tier == "auto":
            tier = self.route(prompt)

        tier_config = self.tiers.get(tier, self.tiers["local"])
        model_name = tier_config["models"].get(self.provider, tier_config["models"]["local"])

        logger.info(f"LLM Router V2: tier={tier}, model={model_name}, provider={self.provider}, prompt='{prompt[:50]}'")

        # Try Ollama if available
        if self.ollama_available and self.provider in ["ollama", "local"]:
            try:
                import ollama
                response = await asyncio.to_thread(
                    self._ollama_generate_sync,
                    prompt,
                    model_name,
                    tier_config["temperature"],
                    tier_config["max_tokens"],
                    system_prompt
                )
                latency = int((time.time() - start) * 1000)
                return LLMResponse(
                    text=response,
                    tier=tier,
                    model=model_name,
                    latency_ms=latency,
                    from_cache=False
                )
            except Exception as e:
                logger.warning(f"Ollama generate failed: {e}, using mock")

        # Fallback mock - Phase 1 style, but tier-aware
        await asyncio.sleep(0.1)  # Simulate latency
        latency = int((time.time() - start) * 1000)

        # Mock responses based on tier
        if tier == "fast":
            mock_text = f"[V2 Fast - {model_name}] Quick response to '{prompt[:50]}'"
        elif tier == "deep":
            mock_text = f"[V2 Deep - {model_name}] Complex reasoning for '{prompt[:50]}': Let me think step by step... 1. Analyze, 2. Plan, 3. Execute. For real deep reasoning, will use {model_name} via Ollama in production."
        else:
            mock_text = f"[V2 {tier.title()} - {model_name}] Response to '{prompt[:80]}': I am OMNI V2, JARVIS KILLER, multi-agent, 100+ tools, chain commands! Phase 2 mock, Phase 3 will use real {model_name} via Ollama local."

        return LLMResponse(
            text=mock_text,
            tier=tier,
            model=model_name,
            latency_ms=latency,
            from_cache=False
        )

    def _ollama_generate_sync(self, prompt: str, model: str, temperature: float, max_tokens: int, system_prompt: str = None) -> str:
        try:
            import ollama
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = ollama.chat(
                model=model,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"Ollama sync generate failed: {e}")
            raise

    def get_status(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "ollama_available": self.ollama_available,
            "tiers": list(self.tiers.keys()),
            "models": {tier: cfg["models"] for tier, cfg in self.tiers.items()}
        }
