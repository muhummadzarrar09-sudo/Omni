#!/usr/bin/env python3
"""
OMNI Whisper Diagnosis
=====================
If OMNI's Whisper can't load, run this. It probes EVERY strategy (GPU + CPU,
with and without CUDA hidden) in isolated processes, so a segfault tells you
exactly which library is broken -- without ever crashing.

    python scripts/whisper_diag.py

It also prints ctranslate2/torch/cuda versions, which pinpoints a mismatch.
"""
import sys
import os
import subprocess

MODEL = "base.en"


def banner(title, char="="):
    print(f"\n{char * 60}\n{title}\n{char * 60}")


def v(modname):
    try:
        m = __import__(modname)
        return getattr(m, "__version__", "unknown")
    except Exception as e:
        return f"NOT INSTALLED ({e})"


def probe(model, device, compute_type, env_extra, timeout_s=180.0):
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
        "    import traceback\n"
        "    traceback.print_exc()\n"
        "    sys.exit(2)\n"
    )
    env = os.environ.copy()
    env.update(env_extra)
    try:
        proc = subprocess.run([sys.executable, "-c", code],
                              capture_output=True, text=True, timeout=timeout_s, env=env)
    except subprocess.TimeoutExpired:
        return ("TIMEOUT", f"timed out after {timeout_s:.0f}s", "")
    except Exception as e:
        return ("ERROR", f"probe could not run: {e}", "")
    rc = proc.returncode
    if rc == 0:
        return ("OK", "loaded + transcribed successfully", "")
    if rc < 0:
        sig = {11: "SIGSEGV (segmentation fault)", 6: "SIGABRT (abort)",
               -1073741819: "Windows 0xC0000005 (access violation)"}.get(-rc, f"signal {-rc}")
        return ("CRASH", sig, "")
    last = (proc.stderr or "").strip()
    return ("FAIL", f"exit code {rc}", last[-800:])


def main():
    banner("OMNI WHISPER DIAGNOSIS")

    banner("Library versions", "-")
    print(f"  Python:          {sys.version.split()[0]}")
    print(f"  faster-whisper:  {v('faster_whisper')}")
    print(f"  ctranslate2:     {v('ctranslate2')}")
    print(f"  torch:           {v('torch')}")
    print(f"  numpy:           {v('numpy')}")

    n_cuda = 0
    try:
        import ctranslate2 as ct2
        n_cuda = ct2.get_cuda_device_count()
        print(f"  CUDA devices:    {n_cuda}")
    except Exception as e:
        print(f"  CUDA devices:    could not query ({e})")

    banner("Probing each strategy in an isolated process", "-")

    strategies = []
    if n_cuda > 0:
        for ct in ["int8", "float32", "int8_float16"]:
            strategies.append(("cuda", ct, {}, f"GPU / {ct}"))
    else:
        print("  (No CUDA devices - skipping GPU probes)\n")
    strategies.append(("cpu", "int8", {"CUDA_VISIBLE_DEVICES": ""}, "CPU / CUDA hidden"))
    strategies.append(("cpu", "int8", {}, "CPU / plain"))

    results = []
    for device, ct, env_extra, label in strategies:
        print(f"  -> Probing {label} ...", flush=True)
        status, detail, stderr = probe(MODEL, device, ct, env_extra)
        results.append((label, status, detail))
        mark = {"OK": "OK  ", "CRASH": "CRASH", "FAIL": "FAIL", "TIMEOUT": "TIME", "ERROR": "ERR "}[status]
        print(f"     [{mark}] {detail}")
        if stderr:
            print(f"     stderr: {stderr.strip().splitlines()[-1][:200]}")
        print()

    # Summary
    banner("SUMMARY")
    working = [l for (l, s, _) in results if s == "OK"]
    if working:
        print(f"  Working strategy found: {working[0]}")
        print(f"  OMNI will use this automatically. You're good to go.")
        return 0

    print("  NO strategy worked. This is a CTranslate2/CUDA/DLL problem, not OMNI's.")
    print("  Most reliable fixes, in order:\n")
    print("    1. Install Microsoft Visual C++ Redistributable (x64):")
    print("       https://aka.ms/vs/17/release/vc_redist.x64.exe")
    print("    2. Clean reinstall of the STT stack:")
    print("       pip uninstall -y faster-whisper ctranslate2")
    print("       pip install faster-whisper==1.0.3")
    print("    3. If CUDA/CPU-hidden differs from plain CPU, your CUDA runtime is")
    print("       broken. Reinstall your NVIDIA driver (Studio or Game Ready).")
    print("    4. Re-run this script to confirm.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
