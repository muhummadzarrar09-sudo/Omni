"""
HF Downloader V2 - Phase 3.5 Turbo - Direct from Hugging Face Hub via HF_TOKEN
Faster than Ollama library, any GGUF, Unsloth quants, gated models
"""

import os
import sys
from pathlib import Path
from typing import Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("HFDownloader")

try:
    from omni_v2.core.paths import DATA_DIR
except ImportError:
    DATA_DIR = Path.home() / ".omni_v2"

MODELS_DIR = DATA_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Model mappings for easy download
MODEL_MAP = {
    "moondream2": {
        "repo_id": "vikhyatk/moondream2",
        "filename": "moondream2-text-model.Q4_K_M.gguf",
        "description": "TurboVLM Moondream2 1.9B - 2GB VRAM, 30-40 tok/s, beats GPT-4o VQAv2",
        "alt_repo": "moondream/moondream2-gguf",
        "alt_filename": "moondream2-text-model-q4_k_m.gguf"
    },
    "qwen2-vl-2b": {
        "repo_id": "Qwen/Qwen2-VL-2B-Instruct-GGUF",
        "filename": "qwen2-vl-2b-instruct.Q4_K_M.gguf",
        "description": "TurboVLM Qwen2-VL-2B - 2B, 4GB VRAM, 90.1% DocVQA, 25-30 tok/s"
    },
    "qwen2.5-vl-3b": {
        "repo_id": "Qwen/Qwen2.5-VL-3B-Instruct-GGUF",
        "filename": "qwen2.5-vl-3b-instruct.Q4_K_M.gguf",
        "description": "TurboVLM Qwen2.5-VL 3B - 3B, 4-8GB VRAM, ~20-25 tok/s, nearly as good as 7B"
    },
    "llama3.1-8b": {
        "repo_id": "TheBloke/Llama-3.1-8B-GGUF",
        "filename": "llama-3.1-8b.Q4_K_M.gguf",
        "description": "LLM Llama 3.1 8B Q4_K_M - General purpose, 8B, 4GB VRAM",
        "unsloth_repo": "unsloth/Llama-3.1-8B-GGUF",
        "unsloth_filename": "llama-3.1-8b.Q4_K_M.gguf"
    },
    "llama3.1-8b-unsloth": {
        "repo_id": "unsloth/Llama-3.1-8B-GGUF",
        "filename": "llama-3.1-8b.Q4_K_M.gguf",
        "description": "LLM Llama 3.1 8B Unsloth Q4_K_M - Higher quality at same size"
    }
}

class HFDownloader:
    """Download GGUF directly from HF Hub via HF_TOKEN - WAY FASTER model selection than Ollama"""

    def __init__(self, token: str = None):
        self.token = token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
        if self.token:
            try:
                from huggingface_hub import login
                login(token=self.token)
                logger.info("HF_TOKEN found - logged in to HF Hub (gated models like Llama 3.1 accessible)")
            except Exception as e:
                logger.warning(f"HF login failed: {e}")
        else:
            logger.info("No HF_TOKEN - can download public models, gated models (Llama 3.1) need token. Set HF_TOKEN env var.")

    def download(self, repo_id: str, filename: str, local_dir: Path = None) -> Optional[Path]:
        """Download single file from HF Hub"""
        local_dir = local_dir or MODELS_DIR
        local_dir.mkdir(parents=True, exist_ok=True)

        try:
            from huggingface_hub import hf_hub_download

            logger.info(f"Downloading {repo_id}/{filename} to {local_dir}... (HF Hub direct, no Ollama)")
            path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=str(local_dir),
                local_dir_use_symlinks=False,
                token=self.token,
                resume_download=True
            )
            p = Path(path)
            size_mb = p.stat().st_size / (1024*1024)
            logger.info(f"Downloaded: {p} ({size_mb:.1f} MB) - HF direct, no Ollama overhead")
            return p

        except ImportError:
            logger.error("huggingface_hub not installed - pip install huggingface_hub")
            return None
        except Exception as e:
            logger.error(f"HF download failed {repo_id}/{filename}: {e}")
            return None

    def download_model(self, model_name: str, quant: str = "Q4_K_M") -> Optional[Path]:
        """Download by friendly name like moondream2, qwen2-vl-2b, llama3.1-8b"""
        model_name = model_name.lower()

        # Find in map
        info = MODEL_MAP.get(model_name)
        if not info:
            # Try partial match
            for k, v in MODEL_MAP.items():
                if model_name in k or k in model_name:
                    info = v
                    model_name = k
                    break

        if not info:
            logger.error(f"Unknown model {model_name}. Known: {list(MODEL_MAP.keys())}")
            return None

        # Adjust filename for quant if needed
        filename = info["filename"]
        if quant != "Q4_K_M" and "Q4_K_M" in filename:
            filename = filename.replace("Q4_K_M", quant)

        logger.info(f"Downloading {model_name}: {info['description']}")

        # Try primary repo
        path = self.download(info["repo_id"], filename)

        # Try alt repo if primary fails
        if not path and "alt_repo" in info:
            logger.info(f"Trying alt repo {info['alt_repo']}")
            path = self.download(info["alt_repo"], info.get("alt_filename", filename))

        # Try unsloth repo for Llama (higher quality)
        if not path and "unsloth_repo" in info:
            logger.info(f"Trying Unsloth repo {info['unsloth_repo']} (higher quality)")
            path = self.download(info["unsloth_repo"], info.get("unsloth_filename", filename))

        if path:
            logger.info(f"Turbo model {model_name} ready at {path} - {info['description']}")
        else:
            logger.error(f"Failed to download {model_name}")

        return path

    def list_downloaded(self):
        """List downloaded models in data/models/"""
        if not MODELS_DIR.exists():
            print(f"No models dir: {MODELS_DIR}")
            return

        print(f"\nDownloaded models in {MODELS_DIR}:")
        for f in MODELS_DIR.glob("*.gguf"):
            size_mb = f.stat().st_size / (1024*1024)
            print(f"  {f.name} ({size_mb:.1f} MB)")

        for f in MODELS_DIR.glob("*.bin"):
            size_mb = f.stat().st_size / (1024*1024)
            print(f"  {f.name} ({size_mb:.1f} MB)")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HF Downloader - Direct from HF Hub via HF_TOKEN - Faster than Ollama")
    parser.add_argument("--model", type=str, default="moondream2", help="Model name: moondream2, qwen2-vl-2b, llama3.1-8b, etc.")
    parser.add_argument("--repo", type=str, help="Repo ID like TheBloke/Llama-3.1-8B-GGUF")
    parser.add_argument("--file", type=str, help="Filename like llama-3.1-8b.Q4_K_M.gguf")
    parser.add_argument("--quant", type=str, default="Q4_K_M", help="Quant: Q4_K_M, Q5_K_M, Q8_0, etc.")
    parser.add_argument("--list", action="store_true", help="List downloaded models")
    parser.add_argument("--token", type=str, help="HF token (or set HF_TOKEN env)")

    args = parser.parse_args()

    downloader = HFDownloader(token=args.token)

    if args.list:
        downloader.list_downloaded()
    elif args.repo and args.file:
        downloader.download(args.repo, args.file)
    else:
        downloader.download_model(args.model, quant=args.quant)
        downloader.list_downloaded()

    print("\nNext: Use with llama.cpp direct for WAY FASTER inference than Ollama!")
    print("  python -m omni_v2.llm.llama_cpp --model data/models/llama-3.1-8b.Q4_K_M.gguf --prompt 'Hello'")
