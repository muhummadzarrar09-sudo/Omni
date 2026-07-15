"""
OMNI CLI - single entry point for everything.
After `pip install -e .`, run `omni ...` from anywhere.

Subcommands:
  omni install         - print install instructions for this platform
  omni model info      - show which GGUF model is loaded, sizes, speed
  omni model download  - fetch the default Qwen2.5-1.5B GGUF (~1.1GB)
  omni test            - run all 4 test suites (10/10 multi-agent + 3 phase tests)
  omni start           - start FastAPI backend (judges can curl it)
  omni ui              - start Next.js dev server
  omni dev             - start both (backend + UI) and open browser
  omni status          - health check
  omni shell           - interactive shell (REPL) into the brain
"""
import argparse
import sys
import subprocess
import time
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

# Fix Windows cp1252 console encoding FIRST (before any module prints emoji)
try:
    from omni_v2.utils.utf8 import setup_utf8_console
    setup_utf8_console()
except Exception:
    pass


def _run(cmd, **kwargs):
    """Run a subprocess, pass through stdout/stderr."""
    return subprocess.run(cmd, **kwargs)


def cmd_install(args):
    """Print install instructions for current platform."""
    import platform
    is_win = platform.system() == "Windows"
    script = "install.ps1" if is_win else "install.sh"
    print(f"\n  OMNI V3 install ({platform.system()})\n")
    print(f"  EASIEST: one-shot install script (handles llama-cpp prebuilt wheel):")
    print(f"     ./{script}")
    if is_win:
        print(f"     # or: .\\{script} -Cuda cu121   # for NVIDIA GPU")
    else:
        print(f"     # or: ./{script} --cuda cu121   # for NVIDIA GPU")
        print(f"     # or: ./{script} --minimal      # just the brain")
    print()
    print(f"  Or, the manual way:")
    print(f"     1. Create venv:")
    print(f"        python -m venv .venv")
    print(f"        {' .venv\\Scripts\\activate' if is_win else 'source .venv/bin/activate'}")
    print()
    print(f"     2. Install llama-cpp-python FIRST (prebuilt wheel, avoids MSVC build):")
    if is_win:
        print(f"        pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu")
    else:
        print(f"        pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu")
    print()
    print(f"     3. Install OMNI + everything:")
    print(f"        pip install -e .[all]")
    print()
    print(f"     4. Download the LLM (one-time, 1.1GB):")
    print(f"        omni model download")
    print()
    print(f"     5. Test:")
    print(f"        omni test")
    print()
    print(f"     6. Run:")
    print(f"        omni start          # FastAPI on :8765")
    print(f"        omni dev            # backend + UI + browser")
    print()
    print(f"  Or, the OLD way (no install needed):")
    print(f"     python omni.py --test    # multi-agent tests")
    print(f"     python run_dev_all.py    # full stack (LEGACY, no longer used)")


def cmd_model_info(args):
    """Show which model is loaded, size, speed, etc."""
    print(f"\n  OMNI Model Status\n")
    model_path = REPO_ROOT / "data" / "models"
    if not model_path.exists():
        print("  ❌ No models/ dir. Run: omni model download")
        return 1
    ggufs = list(model_path.glob("*.gguf"))
    if not ggufs:
        print("  ❌ No GGUF models. Run: omni model download")
        return 1
    print(f"  Models in {model_path}:")
    for g in ggufs:
        size_mb = g.stat().st_size / (1024 * 1024)
        print(f"    {g.name:<50s} {size_mb:>7.0f} MB")
    # Try to load the brain and see what it picked
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from omni_v2.llm.brain import get_brain
        brain = get_brain()
        status = brain.get_status()
        print(f"\n  Brain status:")
        print(f"    Model loaded: {'✅' if status['model_loaded'] else '❌'}")
        print(f"    Tier:        {status['tier']}")
        print(f"    Tools:       {status['tool_count']}")
    except Exception as e:
        print(f"\n  (Brain not loaded: {e})")
    print()
    return 0


def cmd_model_download(args):
    """Download the default Qwen2.5-1.5B GGUF."""
    target = REPO_ROOT / "data" / "models" / "qwen2.5-1.5b-instruct-q4_k_m.gguf"
    if target.exists():
        print(f"  ✅ Already present: {target} ({target.stat().st_size // 1024 // 1024} MB)")
        return 0
    print(f"  Downloading Qwen2.5-1.5B-Instruct Q4_K_M (~1.1GB)...")
    target.parent.mkdir(parents=True, exist_ok=True)
    url = "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=300) as resp:
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(target, "wb") as f:
                chunk_size = 1024 * 64
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = (downloaded / total) * 100
                        print(f"  \r  {pct:5.1f}%  {downloaded // 1024 // 1024} MB / {total // 1024 // 1024} MB", end="", flush=True)
            print()
        print(f"  ✅ Saved to {target}")
        return 0
    except Exception as e:
        print(f"  ❌ Download failed: {e}")
        if target.exists():
            target.unlink()
        return 1


def cmd_test(args):
    """Run all 4 test suites."""
    print("\n  " + "=" * 60)
    print("  OMNI V3 - Full Test Suite")
    print("  " + "=" * 60 + "\n")

    # 1. omni.py --test (multi-agent, 10 commands)
    print("  [1/4] Multi-agent core (omni.py --test)")
    r = _run([sys.executable, str(REPO_ROOT / "omni.py"), "--test"],
             cwd=str(REPO_ROOT), capture_output=True, text=True)
    passed = "10/10" in r.stdout or "PASS" in r.stdout
    print(f"        {'✅ PASS' if passed else '✗ FAIL'}")
    if args.verbose or not passed:
        print(r.stdout[-2000:])

    # 2-4. Phase 6 tests
    test_files = [
        ("FastAF DB (sub-ms semantic lookup)", "omni_v2.tests.test_fast_af_db"),
        ("Hermes refinement (self-healing)",   "omni_v2.tests.test_hermes_refinement"),
        ("Skill synthesis (custom skills)",     "omni_v2.tests.test_skill_synthesis"),
    ]
    all_ok = passed
    for i, (name, module) in enumerate(test_files, start=2):
        print(f"\n  [{i}/4] {name}")
        r = _run([sys.executable, "-m", module],
                 cwd=str(REPO_ROOT), capture_output=True, text=True)
        ok = "PASSED" in r.stdout
        all_ok = all_ok and ok
        print(f"        {'✅ PASS' if ok else '✗ FAIL'}")
        if args.verbose or not ok:
            print(r.stdout[-1500:])
            if r.stderr:
                print("STDERR:", r.stderr[-1000:])

    print("\n  " + "=" * 60)
    print(f"  {'✅ ALL TESTS PASSED' if all_ok else '✗ SOME TESTS FAILED'}")
    print("  " + "=" * 60 + "\n")
    return 0 if all_ok else 1


def cmd_start(args):
    """Start the FastAPI backend."""
    import webbrowser
    print(f"\n  OMNI V3 - FastAPI backend on http://localhost:8765\n")
    if not args.no_browser:
        # Try to open in isolated Chrome
        try:
            sys.path.insert(0, str(REPO_ROOT))
            from omni_v2.tools.browser_v3 import BrowserToolV3
            browser = BrowserToolV3()
            browser._launch_chrome_isolated("http://localhost:8765")
        except Exception:
            webbrowser.open("http://localhost:8765", new=2)
    os.chdir(REPO_ROOT / "backend_fastapi")
    cmd = [sys.executable, "-m", "uvicorn", "main:app",
           "--host", "0.0.0.0", "--port", "8765"]
    if args.reload:
        cmd.append("--reload")
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n  🛑 Stopped")
    return 0


def _find_npm():
    """Locate npm.exe on Windows (venv doesn't put node on PATH)."""
    import shutil
    p = shutil.which("npm")
    if p:
        return p
    # Common Windows install paths
    candidates = [
        Path(os.environ.get("APPDATA", "")) / "npm" / "npm.cmd",
        Path("C:/Program Files/nodejs/npm.cmd"),
        Path("C:/Program Files (x86)/nodejs/npm.cmd"),
    ]
    for c in candidates:
        if c and c.exists():
            return str(c)
    return None


def _ensure_node_modules(frontend: Path) -> bool:
    """Install node_modules if missing. Returns True on success."""
    if (frontend / "node_modules").exists():
        return True
    npm = _find_npm()
    if not npm:
        print(f"  ⚠️  npm not found on PATH. Install Node.js 18+ from https://nodejs.org")
        print(f"      Then run: cd frontend_next && npm install")
        return False
    print(f"  Installing node_modules (first time, 1-2 min) using {npm}...")
    try:
        r = subprocess.run([npm, "install"], cwd=str(frontend), check=True,
                           shell=True if os.name == "nt" else False)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️  npm install failed (exit {e.returncode}). UI won't start.")
        return False


def cmd_ui(args):
    """Start the Next.js UI."""
    print(f"\n  OMNI V3 - Next.js UI on http://localhost:3000\n")
    frontend = REPO_ROOT / "frontend_next"
    if not _ensure_node_modules(frontend):
        return 1
    npm = _find_npm()
    if not npm:
        return 1
    os.chdir(frontend)
    try:
        subprocess.run([npm, "run", "dev"], shell=os.name == "nt")
    except KeyboardInterrupt:
        print("\n  🛑 Stopped")
    return 0


def cmd_dev(args):
    """Start backend + UI, open browser. The 'everything' command."""
    import threading
    import webbrowser
    print(f"\n  OMNI V3 - Dev mode (backend + UI)\n")

    # 1) Backend FIRST (foreground, but we'll background it via thread)
    def run_backend():
        os.chdir(REPO_ROOT / "backend_fastapi")
        subprocess.run([sys.executable, "-m", "uvicorn", "main:app",
                        "--port", "8765", "--host", "0.0.0.0"])
    bt = threading.Thread(target=run_backend, daemon=True)
    bt.start()
    print("  ⏳ Waiting for backend to come up on :8765...")
    time.sleep(4)

    # 2) Try UI (non-fatal if it fails)
    frontend = REPO_ROOT / "frontend_next"
    ui_ready = _ensure_node_modules(frontend)
    npm = _find_npm() if ui_ready else None
    if not npm:
        print("  ⚠️  UI skipped (no npm). Backend at http://localhost:8765 is LIVE.")
        print("  Press Ctrl+C to stop. Open http://localhost:8765/docs in your browser.\n")
        try:
            bt.join()
        except KeyboardInterrupt:
            pass
        return 0

    def open_browser_later():
        time.sleep(5)
        try:
            webbrowser.open("http://localhost:3000", new=2)
        except Exception:
            pass
    threading.Thread(target=open_browser_later, daemon=True).start()

    # 3) UI in foreground
    os.chdir(frontend)
    print("  Starting Next.js UI (Ctrl+C to stop everything)...\n")
    try:
        subprocess.run([npm, "run", "dev"], shell=os.name == "nt")
    except KeyboardInterrupt:
        print("\n  🛑 Stopped")
    return 0


def cmd_status(args):
    """Health check - is the backend running? is the brain loaded?"""
    import urllib.request
    import urllib.error
    print("\n  OMNI Status\n")
    try:
        with urllib.request.urlopen("http://localhost:8765/api/health", timeout=2) as r:
            import json
            data = json.loads(r.read())
            print(f"  Backend:  ✅ Running (brain_ready={data.get('brain_ready')})")
            print(f"  Brain:    {data.get('stt', {}).get('init_status', 'unknown')}")
            print(f"  TTS:      {data.get('tts', {}).get('init_status', 'unknown')}")
            print(f"  Audio:    {data.get('audio', 'unknown')}")
    except urllib.error.URLError:
        print(f"  Backend:  ❌ Not running (start with: omni start)")

    # Check model
    model = REPO_ROOT / "data" / "models" / "qwen2.5-1.5b-instruct-q4_k_m.gguf"
    if model.exists():
        print(f"  LLM:      ✅ {model.name} ({model.stat().st_size // 1024 // 1024} MB)")
    else:
        print(f"  LLM:      ❌ Not found. Run: omni model download")
    print()


def cmd_shell(args):
    """Interactive REPL into the brain."""
    print(f"\n  OMNI Brain REPL (type 'exit' to quit)\n")
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.llm.brain import get_brain
    from omni_v2.core import PluginManager
    from omni_v2.tools import get_all_tools

    pm = PluginManager()
    for t in get_all_tools():
        pm.register(t)
    brain = get_brain(plugin_manager=pm)
    print(f"  Brain ready. Tier: {brain.get_status()['tier']}\n")

    while True:
        try:
            user_input = input("  You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break
        t0 = time.time()
        resp = brain.think(user_input, stream=False)
        dt = (time.time() - t0) * 1000
        if resp.tool_calls:
            print(f"  OMNI [{dt:.0f}ms] tool calls:")
            for tc in resp.tool_calls:
                print(f"     → {tc['tool']}({tc.get('args', {})})")
        else:
            print(f"  OMNI [{dt:.0f}ms]: {resp.text}")
        print()


def main():
    parser = argparse.ArgumentParser(
        prog="omni",
        description="OMNI V3 - Local, Private, Cinematic AGI",
    )
    sub = parser.add_subparsers(dest="cmd", required=False)

    sub.add_parser("install", help="Print install instructions")
    sub.add_parser("status", help="Health check")
    sub.add_parser("test", help="Run all test suites").add_argument(
        "-v", "--verbose", action="store_true", help="Show full output"
    )

    m = sub.add_parser("model", help="Model management")
    m_sub = m.add_subparsers(dest="model_cmd", required=False)
    m_sub.add_parser("info", help="Show loaded model info")
    m_sub.add_parser("download", help="Download default Qwen2.5-1.5B GGUF")

    s = sub.add_parser("start", help="Start FastAPI backend")
    s.add_argument("--no-browser", action="store_true", help="Don't open browser")
    s.add_argument("--reload", action="store_true", help="Enable hot-reload")

    sub.add_parser("ui", help="Start Next.js UI")
    sub.add_parser("dev", help="Start backend + UI (everything)")
    sub.add_parser("shell", help="Interactive brain REPL")

    args = parser.parse_args()
    cmd = args.cmd or "status"

    if cmd == "install":
        return cmd_install(args)
    if cmd == "status":
        return cmd_status(args)
    if cmd == "test":
        return cmd_test(args)
    if cmd == "model":
        sub_cmd = getattr(args, "model_cmd", None) or "info"
        if sub_cmd == "info":
            return cmd_model_info(args)
        if sub_cmd == "download":
            return cmd_model_download(args)
    if cmd == "start":
        return cmd_start(args)
    if cmd == "ui":
        return cmd_ui(args)
    if cmd == "dev":
        return cmd_dev(args)
    if cmd == "shell":
        return cmd_shell(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
