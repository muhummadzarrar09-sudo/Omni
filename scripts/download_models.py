#!/usr/bin/env python3
"""
OMNI Model Downloader
=====================
Downloads all ML model files needed for OMNI to run offline.

Usage:
    python scripts/download_models.py          # Download all models
    python scripts/download_models.py --kokoro # Download Kokoro TTS only
    python scripts/download_models.py --whisper # Download Whisper only
    python scripts/download_models.py --verify  # Verify existing models

Models downloaded:
    1. Kokoro-ONNX TTS (kokoro-tts v1.0)
       - kokoro-v1.0.onnx  (~80MB)
       - voices-v1.0.bin   (~2MB)
       Source: https://github.com/nazdridoy/kokoro-tts/releases/tag/v1.0.0

    2. Faster-Whisper STT (base.en model)
       - Downloaded automatically by faster-whisper on first use
       - Cached at: ~/.cache/huggingface/hub/models--Systran--faster-whisper-base.en
       Source: https://huggingface.co/Systran/faster-whisper-base.en

Exit codes:
    0 = all models downloaded / already present
    1 = download failed
    2 = verification failed
"""

import sys
import os
import hashlib
import argparse
from pathlib import Path

# Color output (cross-platform)
def _color(code: str) -> str:
    return f"\033[{code}m" if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() else ""


RED = _color("31")
GREEN = _color("32")
YELLOW = _color("33")
CYAN = _color("36")
BOLD = _color("1")
RESET = _color("0")


def log(msg: str, color: str = "") -> None:
    prefix = f"{color}{BOLD}[OMNI]{RESET}{color} "
    print(f"{prefix}{msg}{RESET}")


def log_ok(msg: str) -> None:
    log(f"{GREEN}✓{RESET} {msg}", GREEN)


def log_warn(msg: str) -> None:
    log(f"{YELLOW}⚠{RESET} {msg}", YELLOW)


def log_info(msg: str) -> None:
    log(f"{CYAN}ℹ{RESET} {msg}", CYAN)


def log_fail(msg: str) -> None:
    log(f"{RED}✗{RESET} {msg}", RED)


# ─── Model definitions ────────────────────────────────────────────────────────

KOKORO_MODELS = {
    "kokoro-v1.0.onnx": {
        "url": "https://github.com/nazdridoy/kokoro-tts/releases/download/v1.0.0/kokoro-v1.0.onnx",
        "size_mb": 80,
        "description": "Kokoro ONNX TTS model (v1.0)",
    },
    "voices-v1.0.bin": {
        "url": "https://github.com/nazdridoy/kokoro-tts/releases/download/v1.0.0/voices-v1.0.bin",
        "size_mb": 2,
        "description": "Kokoro voice definitions",
    },
}

WHISPER_MODEL = {
    "model_name": "base.en",
    "description": "Faster-Whisper base.en STT model (downloaded on first use)",
    "size_mb": 75,
}

# ─── Utility functions ────────────────────────────────────────────────────────

def get_models_dir() -> Path:
    """Get the models directory path relative to this script."""
    scripts_dir = Path(__file__).resolve().parent  # scripts/
    project_dir = scripts_dir.parent               # omni/ (project root)
    models_dir = project_dir / "models"
    return models_dir


def ensure_dir(path: Path) -> bool:
    """Create directory if it doesn't exist."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        log_fail(f"Cannot create directory {path}: {e}")
        return False


def get_file_size_mb(path: Path) -> float:
    """Get file size in MB."""
    try:
        return path.stat().st_size / (1024 * 1024)
    except Exception:
        return 0.0


def verify_file(path: Path, min_size_mb: float = 0.1) -> tuple[bool, str]:
    """
    Verify a file exists and is non-empty.
    Returns (is_valid, message).
    """
    if not path.exists():
        return False, f"File does not exist: {path}"

    size_mb = get_file_size_mb(path)
    if size_mb < min_size_mb:
        return False, f"File too small ({size_mb:.2f}MB < {min_size_mb}MB): {path}"

    return True, f"OK ({size_mb:.1f}MB)"


# ─── Download with progress ──────────────────────────────────────────────────

def download_file(url: str, dest: Path, min_size_mb: float = 1.0) -> bool:
    """
    Download a file from URL to dest with a progress bar.
    Uses urllib (built-in, no extra deps) with progress reporting.

    Returns True on success, False on failure.
    """
    import urllib.request
    import urllib.error

    log_info(f"Downloading: {Path(url).name}")
    log_info(f"  → {dest}")

    try:
        # Get file size for progress bar
        class _TrackingURLopener(urllib.request.FancyURLopener):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._reporthook = None

        def _progress_hook(count: int, block_size: int, total_size: int):
            if total_size <= 0:
                return
            pct = min(100.0, count * block_size * 100.0 / total_size)
            bar_width = 30
            filled = int(bar_width * pct / 100)
            bar = "█" * filled + "░" * (bar_width - filled)
            # \r without newline — overwrite the line
            print(f"\r  [{bar}] {pct:5.1f}% ", end="", flush=True)
            if pct >= 100:
                print()  # newline after done

        # Download with progress
        urllib.request.urlretrieve(url, dest, _progress_hook)
        print()  # newline after progress bar

        # Verify
        valid, msg = verify_file(dest, min_size_mb)
        if valid:
            log_ok(f"Downloaded: {dest.name} — {msg}")
            return True
        else:
            log_fail(f"Download verification failed: {msg}")
            # Remove corrupted file
            try:
                dest.unlink()
            except Exception:
                pass
            return False

    except urllib.error.URLError as e:
        log_fail(f"Network error: {e}")
        log_info("Check your internet connection and try again.")
        return False
    except Exception as e:
        log_fail(f"Download failed: {e}")
        return False


# ─── Kokoro download ──────────────────────────────────────────────────────────

def download_kokoro(models_dir: Path, force: bool = False) -> bool:
    """Download Kokoro TTS model files."""
    print()
    log(f"{BOLD}Kokoro-ONNX TTS Model Download{RESET}", CYAN)
    print("=" * 50)

    if not ensure_dir(models_dir):
        return False

    all_ok = True
    for filename, info in KOKORO_MODELS.items():
        dest = models_dir / filename

        # Check if already present
        if dest.exists() and not force:
            size_mb = get_file_size_mb(dest)
            if size_mb >= info["size_mb"] * 0.8:  # Allow 80% tolerance
                log_ok(f"{filename} already present ({size_mb:.1f}MB)")
                continue
            else:
                log_warn(f"{filename} is smaller than expected ({size_mb:.1f}MB < {info['size_mb']}MB), re-downloading...")

        log_info(f"Downloading {info['description']} (~{info['size_mb']}MB)...")
        ok = download_file(info["url"], dest, min_size_mb=info["size_mb"] * 0.3)
        if not ok:
            all_ok = False

    return all_ok


# ─── Whisper download ─────────────────────────────────────────────────────────

def download_whisper(models_dir: Path, force: bool = False) -> bool:
    """Trigger faster-whisper to download the base.en model."""
    print()
    log(f"{BOLD}Faster-Whisper STT Model Download{RESET}", CYAN)
    print("=" * 50)

    # Faster-whisper downloads models on first use — just verify it's installed
    try:
        from faster_whisper import WhisperModel
        log_info(f"faster-whisper installed, model: {WHISPER_MODEL['model_name']}")
        log_info("Model will be downloaded on first OMNI run (~75MB)")
        log_info(f"Cached at: ~/.cache/huggingface/hub/")
        log_ok(f"Whisper model will be auto-downloaded. No action needed.")
        return True
    except ImportError:
        log_fail("faster-whisper is not installed.")
        log_info("Run: pip install faster-whisper")
        return False


# ─── Verification ─────────────────────────────────────────────────────────────

def verify_all(models_dir: Path) -> bool:
    """Verify all model files are present and valid."""
    print()
    log(f"{BOLD}Model Verification{RESET}", CYAN)
    print("=" * 50)

    all_ok = True

    # Kokoro
    print(f"\n{CYAN}Kokoro-ONNX TTS:{RESET}")
    for filename, info in KOKORO_MODELS.items():
        path = models_dir / filename
        valid, msg = verify_file(path, min_size_mb=info["size_mb"] * 0.5)
        if valid:
            log_ok(f"  {filename}: {msg}")
        else:
            log_fail(f"  {filename}: {msg}")
            all_ok = False

    # Whisper (check HuggingFace cache)
    print(f"\n{CYAN}Whisper STT:{RESET}")
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    whisper_found = False
    if hf_cache.exists():
        for cached_model in hf_cache.iterdir():
            if "faster-whisper" in str(cached_model) and "base.en" in str(cached_model):
                # Check for model.bin or similar
                for ext in ("*.bin", "*.pt", "*.onnx"):
                    files = list(cached_model.rglob(ext))
                    if files:
                        size_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)
                        log_ok(f"  {WHISPER_MODEL['model_name']}: {size_mb:.0f}MB cached")
                        whisper_found = True
                        break
    if not whisper_found:
        log_warn(f"  {WHISPER_MODEL['model_name']}: Not cached yet — will download on first run")
        all_ok = False  # Not a hard fail — first run handles it

    print()
    if all_ok:
        log_ok("All models verified! OMNI is ready to run.")
    else:
        log_warn("Some models are missing. Run download_models.py to fetch them.")

    return all_ok


def print_status(models_dir: Path) -> None:
    """Print current model status without downloading."""
    print()
    log(f"{BOLD}OMNI Model Status{RESET}", CYAN)
    print("=" * 50)

    # Kokoro
    print(f"\n{CYAN}Kokoro-ONNX TTS:{RESET}")
    kokoro_ok = True
    for filename, info in KOKORO_MODELS.items():
        path = models_dir / filename
        if path.exists():
            size_mb = get_file_size_mb(path)
            status = f"{GREEN}✓{RESET}" if size_mb >= info["size_mb"] * 0.5 else f"{YELLOW}⚠ (too small){RESET}"
            print(f"  {status} {filename} ({size_mb:.1f}MB)")
        else:
            print(f"  {RED}✗{RESET} {filename} — MISSING (~{info['size_mb']}MB)")
            kokoro_ok = False

    if not kokoro_ok:
        print(f"\n  {YELLOW}→ Run: python scripts/download_models.py --kokoro{RESET}")

    # Whisper
    print(f"\n{CYAN}Whisper STT:{RESET}")
    from faster_whisper import WhisperModel
    print(f"  {GREEN}✓{RESET} faster-whisper installed (model auto-downloads on first use)")

    # Summary
    print()
    models_ok = kokoro_ok
    if models_ok:
        log_ok("All TTS models present. OMNI TTS will use Kokoro-ONNX.")
    else:
        log_warn("Kokoro models missing — TTS will fall back to Windows SAPI.")
        log_info(f"Model files should be in: {models_dir}")
        log_info("Run: python scripts/download_models.py --kokoro")


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download OMNI ML model files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/download_models.py           # Download all
  python scripts/download_models.py --kokoro  # Kokoro TTS only
  python scripts/download_models.py --verify  # Verify existing models
  python scripts/download_models.py --status  # Show model status
        """,
    )
    parser.add_argument("--kokoro",  action="store_true", help="Download Kokoro TTS models")
    parser.add_argument("--whisper", action="store_true", help="Check Whisper model")
    parser.add_argument("--verify",  action="store_true", help="Verify all model files")
    parser.add_argument("--status",  action="store_true", help="Show model status")
    parser.add_argument("--all",     action="store_true", help="Download all models (default)")
    parser.add_argument("--force",   action="store_true", help="Re-download even if present")

    args = parser.parse_args()

    # Default: download all if no specific flag
    download_all = args.all or not any([args.kokoro, args.whisper, args.verify, args.status])

    models_dir = get_models_dir()

    # Status mode
    if args.status:
        print_status(models_dir)
        return 0

    # Verify mode
    if args.verify:
        ok = verify_all(models_dir)
        return 0 if ok else 2

    # Download Kokoro
    if args.kokoro or download_all:
        ok = download_kokoro(models_dir, force=args.force)
        if not ok:
            log_warn("Kokoro download had errors. TTS will fall back to Windows SAPI.")

    # Check Whisper
    if args.whisper or download_all:
        download_whisper(models_dir)

    # Final verification
    if download_all:
        print()
        verify_all(models_dir)

    print()
    log_ok("Done! Run 'python omni.py' to start OMNI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())