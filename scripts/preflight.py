#!/usr/bin/env python3
"""
OMNI Pre-Flight Diagnostic
==========================
Run this BEFORE you present. It checks every subsystem and tells you, in plain
English, whether OMNI will work on this machine -- without ever crashing.

    python scripts/preflight.py

It reuses the EXACT same crash-safe load logic that WhisperSTT uses at runtime:
every Whisper strategy (GPU variants AND CPU) is probed in an isolated child
process. A segfault there kills only the disposable probe, never the app.

Exit code 0 = demo-ready. Non-zero = something needs fixing (and it tells you what).
"""
import sys
import os
import subprocess
import importlib
import shutil
from pathlib import Path

# -- Pretty terminal output ---------------------------------------------------
def _c(code: str) -> str:
    return f"\033[{code}m" if sys.stdout.isatty() else ""

GREEN, RED, YELLOW, CYAN, BOLD, DIM, RESET = (
    _c("32"), _c("31"), _c("33"), _c("36"), _c("1"), _c("2"), _c("0")
)

RESULTS = []  # (name, ok, detail)


def check(name, ok, detail=""):
    mark = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    line = f"  {mark} {BOLD}{name}{RESET}"
    if detail:
        line += f"  {DIM}- {detail}{RESET}"
    print(line)
    RESULTS.append((name, ok, detail))


def section(title):
    print(f"\n{CYAN}{BOLD}== {title} =={RESET}")


def can_import(modname) -> bool:
    try:
        importlib.import_module(modname)
        return True
    except Exception:
        return False


def cuda_device_count() -> int:
    """NOTE: the module is spelled 'ctranslate2' (translate, with an 'a')."""
    try:
        import ctranslate2 as ct2
        return ct2.get_cuda_device_count()
    except Exception:
        return 0


def probe_load(model, device, compute_type, env_extra, timeout_s=150.0):
    """
    Probe ONE Whisper load strategy in an ISOLATED child process.
    Returns (ok, detail). Segfaults / timeouts return ok=False, app unaffected.
    Mirrors WhisperSTT._probe_load exactly so green here == green on stage.
    """
    code = (
        "import sys\n"
        "try:\n"
        "    import numpy as np\n"
        "    from faster_whisper import WhisperModel\n"
        f"    m = WhisperModel({model!r}, device={device!r}, compute_type={compute_type!r})\n"
        "    segs = m.transcribe(np.zeros(8000, dtype=np.float32), language='en', beam_size=1, vad_filter=False)[0]\n"
        "    list(segs)\n"
        "    del m\n"
        "    sys.exit(0)\n"
        "except SystemExit:\n"
        "    raise\n"
        "except BaseException as e:\n"
        "    print(f'PROBE_ERROR: {type(e).__name__}: {e}', file=sys.stderr)\n"
        "    sys.exit(2)\n"
    )
    env = os.environ.copy()
    env.update(env_extra)
    try:
        proc = subprocess.run([sys.executable, "-c", code],
                              capture_output=True, text=True, timeout=timeout_s, env=env)
    except subprocess.TimeoutExpired:
        return (False, f"timed out after {timeout_s:.0f}s")
    except Exception as e:
        return (False, f"probe could not run: {e}")
    rc = proc.returncode
    if rc == 0:
        return (True, "ok")
    if rc < 0:
        sig = {11: "SIGSEGV", 6: "SIGABRT"}.get(-rc, f"signal {-rc}")
        return (False, f"CRASHED ({sig})")
    line = (proc.stderr or "").strip().splitlines()
    line = line[-1] if line else f"exit code {rc}"
    return (False, line[:240])


def main():
    print(f"{BOLD}{CYAN}+==========================================+{RESET}")
    print(f"{BOLD}{CYAN}|   OMNI PRE-FLIGHT DIAGNOSTIC             |{RESET}")
    print(f"{BOLD}{CYAN}+==========================================+{RESET}")

    whisper_model = "base.en"

    # -- Python ----------------------------------------------------------------
    section("Python Runtime")
    v = sys.version_info
    check("Python version", v >= (3, 10), f"{v.major}.{v.minor}.{v.micro} (need 3.10+)")

    # -- Dependencies ----------------------------------------------------------
    section("Dependencies")
    deps = [
        ("PyQt5", "PyQt5"),
        ("faster-whisper", "faster_whisper"),
        ("PyAudio", "pyaudio"),
        ("numpy", "numpy"),
        ("loguru", "loguru"),
        ("keyboard", "keyboard"),
        ("psutil", "psutil"),
        ("sentence-transformers", "sentence_transformers"),
    ]
    for label, mod in deps:
        present = can_import(mod)
        check(label, present, "installed" if present else "MISSING - pip install")

    for label, mod in [("kokoro-onnx (TTS)", "kokoro_onnx"), ("pyttsx3 (TTS fallback)", "pyttsx3"),
                       ("sounddevice", "sounddevice"), ("torch", "torch")]:
        present = can_import(mod)
        check(label, True, "installed" if present else "not installed (optional)")

    # -- ctranslate2 version (helps diagnose mismatches) ----------------------
    try:
        import ctranslate2 as ct2
        check("ctranslate2", True, f"v{getattr(ct2, '__version__', '?')}")
    except Exception:
        check("ctranslate2", False, "not importable (faster-whisper needs it)")

    # -- Microphone ------------------------------------------------------------
    section("Audio Input (Microphone)")
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        n = pa.get_device_count()
        mics = [pa.get_device_info_by_index(i) for i in range(n)
                if pa.get_device_info_by_index(i).get("maxInputChannels", 0) > 0]
        default = None
        try:
            default = pa.get_default_input_device_info() if mics else None
        except Exception:
            pass
        pa.terminate()
        check("Microphone detected", len(mics) > 0, f"{len(mics)} input device(s)")
        if default:
            check("Default input device set", True, default.get("name", "?"))
        elif mics:
            check("Default input device set", False,
                  f"none set - OMNI will use {mics[0].get('name', 'first mic')}")
    except Exception as e:
        check("PyAudio input", False, f"{e}")

    # -- THE critical check: actually load Whisper (GPU + CPU), crash-safe -----
    section("Whisper Load Test (the make-or-break check)")
    print(f"  {DIM}Probing each strategy in an isolated process...{RESET}")

    strategies = []
    if cuda_device_count() > 0:
        for ct in ["int8", "float32", "int8_float16"]:
            strategies.append(("cuda", ct, {}, f"GPU/{ct}"))
    else:
        print(f"  {DIM}(No CUDA devices detected - skipping GPU probes){RESET}")

    # CPU with CUDA hidden first (dodges the most common CPU segfault), then plain CPU.
    strategies.append(("cpu", "int8", {"CUDA_VISIBLE_DEVICES": ""}, "CPU (CUDA hidden)"))
    strategies.append(("cpu", "int8", {}, "CPU (plain)"))

    chosen_label = None
    whisper_ok = False
    for device, ct, env_extra, label in strategies:
        ok, detail = probe_load(whisper_model, device, ct, env_extra)
        if ok:
            print(f"     {GREEN}+ {label}: OK{RESET}")
            if not chosen_label:
                chosen_label = label
                whisper_ok = True
        else:
            mark = "CRASH" if detail.startswith("CRASHED") else "fail"
            color = RED if detail.startswith("CRASHED") else YELLOW
            print(f"     {color}- {label}: {detail}{RESET}")

    check("Whisper loads (any strategy)", whisper_ok,
          f"will use: {chosen_label}" if chosen_label else "ALL FAILED - see scripts/whisper_diag.py")

    # -- Model cache -----------------------------------------------------------
    section("Model Cache")
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    whisper_cached = any("whisper" in p.name.lower() for p in hf_cache.glob("*")) if hf_cache.exists() else False
    check("Whisper base.en cached", whisper_cached,
          "ready (offline)" if whisper_cached else "will download on first run (~140MB)")

    omni_dir = Path.home() / ".omni"
    check("OMNI config dir", True, str(omni_dir) if omni_dir.exists() else "created on first run")

    # -- Browser ---------------------------------------------------------------
    section("Browser Automation (optional)")
    chrome_paths = [
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
    ]
    chrome = any(p.exists() for p in chrome_paths) or bool(shutil.which("chrome") or shutil.which("google-chrome"))
    check("Chrome installed", chrome, "" if chrome else "needed for browser commands")

    # -- Verdict ---------------------------------------------------------------
    section("VERDICT")
    blockers = [n for (n, ok, _) in RESULTS if not ok and n in {
        "Python version", "faster-whisper", "ctranslate2", "PyAudio", "Microphone detected",
        "Whisper loads (any strategy)",
    }]
    if not blockers:
        print(f"  {GREEN}{BOLD}+ DEMO-READY.{RESET} Whisper will run: {chosen_label}.")
        print(f"  {DIM}Launch with: python omni.py{RESET}")
        return 0
    else:
        print(f"  {RED}{BOLD}X NOT READY.{RESET} Fix these before presenting:")
        for b in blockers:
            print(f"     - {b}")
        print(f"  {DIM}Detailed Whisper diagnosis: python scripts/whisper_diag.py{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
