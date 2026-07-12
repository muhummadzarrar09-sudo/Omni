"""LLaVA Vision Model V2 - Phase 3 Started - Screen Understanding"""
from typing import Tuple, Optional
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("LLaVAV2")

class LLaVAVision:
    """Vision model for screen description and element finding - Phase 3"""

    def __init__(self, model: str = "llava:7b"):
        self.model = model
        self.ollama_available = False
        self._init_ollama()
        logger.info(f"LLaVAVision V2 - Model: {model}, Ollama: {self.ollama_available} - Phase 3 mock, Phase 4 real")

    def _init_ollama(self):
        try:
            import ollama
            try:
                client = ollama.Client()
                # Check if llava model exists
                models = client.list()
                model_names = [m['name'] for m in models.get('models', [])]
                if any('llava' in name.lower() or 'moondream' in name.lower() for name in model_names):
                    self.ollama_available = True
                    logger.info(f"LLaVA model found in Ollama: {model_names}")
                else:
                    logger.warning(f"No LLaVA model in Ollama, found: {model_names[:3]} - will use mock")
                    self.ollama_available = False
            except Exception as e:
                logger.warning(f"Ollama not running: {e} - using mock vision")
                self.ollama_available = False
        except ImportError:
            logger.warning("ollama not installed - pip install ollama - using mock vision")
            self.ollama_available = False

    async def describe_screen(self, image=None) -> str:
        """Describe what's on screen"""
        if self.ollama_available:
            try:
                # Real LLaVA via Ollama
                import ollama
                import base64
                from io import BytesIO

                # If image is PIL, encode to base64
                if image:
                    buffered = BytesIO()
                    image.save(buffered, format="PNG")
                    img_b64 = base64.b64encode(buffered.getvalue()).decode()

                    response = ollama.chat(
                        model=self.model,
                        messages=[
                            {"role": "user", "content": "Describe what's on this screen in detail. What apps are open? What is the user doing?", "images": [img_b64]}
                        ]
                    )
                    desc = response['message']['content']
                    logger.info(f"LLaVA real description: {desc[:100]}")
                    return desc
            except Exception as e:
                logger.warning(f"LLaVA real failed: {e}, using mock")

        # Mock for demo / fallback - looks at window titles for demo
        try:
            # Try to get active window title via pygetwindow
            import pygetwindow as gw
            windows = gw.getAllTitles()
            # Filter out empty
            windows = [w for w in windows if w.strip()][:5]
            if windows:
                return f"I see {len(windows)} windows: {', '.join(windows[:3])}. OMNI V2 HUD is glowing. (Phase 3 mock - Phase 4 will use real LLaVA {self.model})"
        except Exception:
            pass

        return "I see VS Code with main.py open, Chrome with YouTube behind, and OMNI V2 HUD glowing blue. The system dashboard shows CPU 15% and memory 4GB free. (Phase 3 mock - will use real LLaVA vision in production)"

    async def find_element(self, query: str, image=None) -> Optional[Tuple[int, int]]:
        """Find element like 'login button' and return coordinates"""
        # Phase 3: Mock
        # Phase 4: Use OWLv2 or YOLO + CLIP to find element coordinates
        logger.info(f"Find element '{query}' - Phase 3 mock, will return center screen")
        # Return center of screen as mock
        try:
            import pyautogui
            w, h = pyautogui.size()
            return (w//2, h//2)
        except Exception:
            return (960, 540)

if __name__ == "__main__":
    import asyncio
    async def test():
        vision = LLaVAVision()
        desc = await vision.describe_screen()
        print(f"Description: {desc}")
        coords = await vision.find_element("login button")
        print(f"Login button at: {coords}")

    asyncio.run(test())
