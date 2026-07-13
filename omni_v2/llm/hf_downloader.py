"""
HF Downloader V2 - Phase 3.5 Turbo FIXED - Correct GGUF repos + HF_TOKEN handling
Fixes:
- Correct repo IDs from research: bartowski, ggml-org, etc.
- Handles invalid HF_TOKEN gracefully (fallback to unauthenticated)
- Removes deprecated args (resume_download, local_dir_use_symlinks)
- Provides prebuilt llama-cpp-python install fix
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

# FIXED MODEL MAP - Correct repos from HF Hub research
MODEL_MAP = {
    "moondream2": {
        "repo_id": "ggml-org/moondream2-20250414-GGUF",
        "filename": "moondream2-20250414-Q4_K_M.gguf",
        "description": "TurboVLM Moondream2 1.9B - 2GB VRAM, 30-40 tok/s, beats GPT-4o VQAv2",
        "alt_repos": [
            ("vikhyatk/moondream2", "moondream2-text-model.f16.gguf"),  # Original pytorch, not GGUF but works with transformers
            ("moondream/moondream-2b-2025-04-14-4bit", "moondream2-mmproj-f16.gguf"),
            ("abhi0127/moondream2", "moondream2-mmproj-f16.gguf"),
        ]
    },
    "qwen2-vl-2b": {
        "repo_id": "bartowski/Qwen2-VL-2B-Instruct-GGUF",
        "filename": "Qwen2-VL-2B-Instruct-Q4_K_M.gguf",
        "description": "TurboVLM Qwen2-VL-2B - 2B, 4GB VRAM, 90.1% DocVQA, 25-30 tok/s",
        "alt_repos": [
            ("tensorblock/Qwen2-VL-2B-GGUF", "Qwen2-VL-2B-Q4_K_M.gguf"),
            ("matrixportalx/Qwen2-VL-2B-Instruct-GGUF", "qwen2-vl-2b-instruct-q4_k_m.gguf"),
            ("Qwen/Qwen2-VL-2B-Instruct", "model.safetensors"),  # Transformers version fallback
        ]
    },
    "qwen2.5-vl-3b": {
        "repo_id": "bartowski/Qwen2.5-VL-3B-Instruct-GGUF",
        "filename": "Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf",
        "description": "TurboVLM Qwen2.5-VL 3B - 3B, 4-8GB VRAM, ~20-25 tok/s",
        "alt_repos": [
            ("Mungert/Qwen2.5-VL-3B-Instruct-GGUF", "Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf"),
        ]
    },
    "llama3.1-8b": {
        "repo_id": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
        "filename": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "description": "LLM Llama 3.1 8B Q4_K_M - 8B, 4GB VRAM, general purpose",
        "alt_repos": [
            ("TheBloke/Llama-3.1-8B-GGUF", "llama-3.1-8b.Q4_K_M.gguf"),
            ("unsloth/Meta-Llama-3.1-8B-GGUF", "meta-llama-3.1-8b.Q4_K_M.gguf"),
        ]
    },
    "llama3.1-8b-unsloth": {
        "repo_id": "unsloth/Meta-Llama-3.1-8B-GGUF",
        "filename": "meta-llama-3.1-8b.Q4_K_M.gguf",
        "description": "LLM Llama 3.1 8B Unsloth Q4_K_M - Higher quality (Unsloth quants)",
        "alt_repos": [
            ("bartowski/Meta-Llama-3.1-8B-Instruct-GGUF", "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"),
        ]
    },
    "llama3.2-3b": {
        "repo_id": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "filename": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "description": "LLM Llama 3.2 3B Q4_K_M - 3B, 2GB VRAM, super fast for 1050 Ti"
    }
}

class HFDownloader:
    def __init__(self, token: str = None):
        self.token = token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
        self.authenticated = False

        if self.token:
            # Validate token is not placeholder
            if self.token in ["hf_xxx", "hf_xxx", "xxx", ""] or len(self.token) < 10:
                logger.warning(f"HF_TOKEN looks like placeholder '{self.token}' - ignoring, will try unauthenticated (public models only)")
                self.token = None
            else:
                try:
                    from huggingface_hub import login
                    login(token=self.token)
                    self.authenticated = True
                    logger.info(f"HF_TOKEN found (length {len(self.token)}) - logged in, gated models accessible")
                except Exception as e:
                    logger.warning(f"HF login failed: {e} - trying unauthenticated for public models")
                    # Don't fail, try unauthenticated for public models
                    self.token = None
        else:
            logger.info("No HF_TOKEN - can download public models, gated models (Llama 3.1) need token. Set HF_TOKEN env var from https://huggingface.co/settings/tokens")

    def download(self, repo_id: str, filename: str, local_dir: Path = None) -> Optional[Path]:
        local_dir = local_dir or MODELS_DIR
        local_dir.mkdir(parents=True, exist_ok=True)

        try:
            from huggingface_hub import hf_hub_download

            logger.info(f"Downloading {repo_id}/{filename} to {local_dir}...")

            # FIXED: Removed deprecated args resume_download and local_dir_use_symlinks
            path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=str(local_dir),
                token=self.token,
                # resume_download is deprecated and ignored - downloads always resume
                # local_dir_use_symlinks is deprecated - not needed
            )
            p = Path(path)
            size_mb = p.stat().st_size / (1024*1024)
            logger.info(f"Downloaded: {p.name} ({size_mb:.1f} MB) from {repo_id}")
            return p

        except ImportError:
            logger.error("huggingface_hub not installed - pip install huggingface_hub")
            return None
        except Exception as e:
            logger.debug(f"HF download failed {repo_id}/{filename}: {e}")
            return None

    def download_model(self, model_name: str, quant: str = "Q4_K_M") -> Optional[Path]:
        model_name = model_name.lower().strip()
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
            logger.info("Try: --repo REPO_ID --file FILENAME for custom")
            return None

        # Adjust filename for quant if needed
        filename = info["filename"]
        if quant != "Q4_K_M" and "Q4_K_M" in filename:
            filename = filename.replace("Q4_K_M", quant)

        logger.info(f"Downloading {model_name}: {info['description']}")
        logger.info(f"Primary: {info['repo_id']}/{filename}")

        # Try primary
        path = self.download(info["repo_id"], filename)
        if path and path.exists():
            logger.info(f"Turbo model {model_name} ready at {path}")
            return path

        # Try alt repos
        for alt_repo, alt_file in info.get("alt_repos", []):
            # Adjust alt file for quant too
            if quant != "Q4_K_M" and "Q4_K_M" in alt_file:
                alt_file_q = alt_file.replace("Q4_K_M", quant)
            else:
                alt_file_q = alt_file

            logger.info(f"Trying alt: {alt_repo}/{alt_file_q}")
            path = self.download(alt_repo, alt_file_q)
            if path and path.exists():
                logger.info(f"Turbo model {model_name} ready via alt {alt_repo} at {path}")
                return path

        logger.error(f"Failed to download {model_name} from all repos")
        logger.info(f"Try manual download from https://huggingface.co/{info['repo_id']}/tree/main")
        logger.info(f"Place file in {MODELS_DIR}/")
        return None

    def list_downloaded(self):
        if not MODELS_DIR.exists():
            print(f"No models dir: {MODELS_DIR}")
            return

        print(f"\nDownloaded models in {MODELS_DIR}:")
        found = False
        for f in MODELS_DIR.glob("*.gguf"):
            size_mb = f.stat().st_size / (1024*1024)
            print(f"  ✓ {f.name} ({size_mb:.1f} MB)")
            found = True

        for f in MODELS_DIR.glob("*.bin"):
            size_mb = f.stat().st_size / (1024*1024)
            print(f"  ✓ {f.name} ({size_mb:.1f} MB)")
            found = True

        if not found:
            print("  (none yet)")

        print(f"\nFor llama.cpp direct (WAY FASTER than Ollama):")
        print(f"  python -m omni_v2.llm.llama_cpp --model {MODELS_DIR}/<model>.gguf --prompt 'Hello'")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HF Downloader FIXED - Correct GGUF repos, handles invalid token, no deprecated args")
    parser.add_argument("--model", type=str, default="moondream2", help="Model: moondream2, qwen2-vl-2b, llama3.1-8b, llama3.2-3b, etc.")
    parser.add_argument("--repo", type=str, help="Custom repo ID")
    parser.add_argument("--file", type=str, help="Custom filename")
    parser.add_argument("--quant", type=str, default="Q4_K_M", help="Quant: Q4_K_M, Q5_K_M, Q8_0, etc.")
    parser.add_argument("--list", action="store_true", help="List downloaded models")
    parser.add_argument("--token", type=str, help="HF token (or set HF_TOKEN env)")

    args = parser.parse_args()

    downloader = HFDownloader(token=args.token)

    if args.list:
        downloader.list_downloaded()
    elif args.repo and args.file:
        path = downloader.download(args.repo, args.file)
        if path:
            print(f"Downloaded to {path}")
        downloader.list_downloaded()
    else:
        path = downloader.download_model(args.model, quant=args.quant)
        if path:
            print(f"\n✓ Downloaded {args.model} to {path}")
        downloader.list_downloaded()

    print("\nNext steps:")
    print("1. For LLM (WAY FASTER than Ollama):")
    print("   pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121 (CUDA)")
    print("   OR pip install llama-cpp-python (CPU)")
    print("   If build fails, need Visual Studio Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/")
    print("   Desktop development with C++ workload")
    print("")
    print("2. For Vision (TurboVLM EVEN FASTER than LLaVA):")
    print("   pip install moondream  # For Moondream2")
    print("   pip install transformers qwen-vl-utils  # For Qwen2-VL")
    print("")
    print("3. Test turbo:")
    print("   python -m omni_v2.llm.llama_cpp --model data/models/<model>.gguf --prompt 'Hello' --benchmark")
    print("   python -m omni_v2.vision.turbovlm --model moondream2 --benchmark")
