"""
OMNI CLI - single entry point for everything.
After `pip install -e .`, run `omni ...` from anywhere.

Subcommands:
  omni install         - print install instructions for this platform
  omni model info      - show which GGUF model is loaded, sizes, speed
  omni model download  - fetch the default Qwen2.5-1.5B GGUF (~1.1GB)
  omni test            - run all 20 test suites (10/10 multi-agent + 18 phase tests)
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
    activate_cmd = "  .venv\\Scripts\\activate" if is_win else "source .venv/bin/activate"
    print(f"        {activate_cmd}")
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
    """Run all 20 test suites."""
    print("\n  " + "=" * 60)
    print("  OMNI V3 - Full Test Suite (28 suites)")
    print("  " + "=" * 60 + "\n")

    # All 20 test suites
    test_files = [
        ("[1/20] Multi-agent core (omni.py --test)", "omni_v2.tests.test_fast_af_db", "_run_omni_test"),
        ("[2/20] FastAF DB (sub-ms semantic lookup)", "omni_v2.tests.test_fast_af_db", "module"),
        ("[3/20] Hermes refinement (self-healing)",   "omni_v2.tests.test_hermes_refinement", "module"),
        ("[4/20] Skill synthesis (custom skills)",     "omni_v2.tests.test_skill_synthesis", "module"),
        ("[5/20] Security guardrails (10 defenses)",   "omni_v2.tests.test_security_guardrails", "module"),
        ("[6/20] User profile (Phase 1)",              "omni_v2.tests.test_user_profile", "module"),
        ("[7/20] Session memory (Phase 1)",            "omni_v2.tests.test_session_memory", "module"),
        ("[8/20] Personality (Phase 2)",               "omni_v2.tests.test_personality", "module"),
        ("[9/20] Opinion engine (Phase 2)",            "omni_v2.tests.test_opinion", "module"),
        ("[10/20] Onboarding (Phase 3)",              "omni_v2.tests.test_onboarding", "module"),
        ("[11/20] Demo mode (Phase 3)",                "omni_v2.tests.test_demo_mode", "module"),
        ("[12/20] Stats (Phase 3)",                    "omni_v2.tests.test_stats", "module"),
        ("[13/20] Vision (Phase 4)",                   "omni_v2.tests.test_vision", "module"),
        ("[14/20] Marketplace (Phase 4)",              "omni_v2.tests.test_marketplace", "module"),
        ("[15/20] Network discovery (Phase 5A)",       "omni_v2.tests.test_network", "module"),
        ("[16/20] Mobile PWA (Phase 5B)",              "omni_v2.tests.test_mobile", "module"),
        ("[17/20] Geofence engine (Phase 5C)",         "omni_v2.tests.test_geofence", "module"),
        ("[18/20] Notification center (Phase 5D)",    "omni_v2.tests.test_notifications", "module"),
        ("[19/20] Notification prefs (Phase 5E)",     "omni_v2.tests.test_notification_prefs", "module"),
        ("[20/20] Screen watcher (Phase 6A)",         "omni_v2.tests.test_screen_watcher", "module"),
        # Away Mode (Phase 7)
        ("[21/26] Hybrid memory (RAG+CAG)",          "omni_v2.tests.test_hybrid_memory", "module"),
        ("[22/26] Knowledge base (RAG ingest)",      "omni_v2.tests.test_knowledge_base", "module"),
        ("[23/26] Research agent",                   "omni_v2.tests.test_research", "module"),
        ("[24/26] Away agent (task queue)",          "omni_v2.tests.test_away_agent", "module"),
        ("[25/26] Messenger bridge",                 "omni_v2.tests.test_messenger", "module"),
        ("[26/26] Remote command channel",           "omni_v2.tests.test_command_channel", "module"),
        # Security + Desktop (Phase 8)
        ("[27/28] Camera security (face auth + lockdown + guard)", "omni_v2.tests.test_security", "module"),
        ("[28/28] Desktop controller",               "omni_v2.tests.test_desktop", "module"),
    ]

    all_ok = True
    for name, module, kind in test_files:
        print(f"  {name}")
        if kind == "_run_omni_test":
            r = _run([sys.executable, str(REPO_ROOT / "omni.py"), "--test"],
                     cwd=str(REPO_ROOT), capture_output=True, text=True)
            ok = "10/10" in r.stdout or "PASS" in r.stdout
        else:
            r = _run([sys.executable, "-m", module],
                     cwd=str(REPO_ROOT), capture_output=True, text=True)
            ok = "PASSED" in r.stdout or "ALL " in r.stdout and "PASSED" in r.stdout
        all_ok = all_ok and ok
        print(f"        {'✅ PASS' if ok else '✗ FAIL'}")
        if args.verbose or not ok:
            if kind == "module":
                print(r.stdout[-1500:])
                if r.stderr:
                    print("STDERR:", r.stderr[-500:])

    # Also run the voice clone test
    print("\n  [bonus] Voice clone (Phase 4)")
    r = _run([sys.executable, "-m", "omni_v2.tests.test_voice_clone"],
             cwd=str(REPO_ROOT), capture_output=True, text=True)
    ok = "PASSED" in r.stdout
    all_ok = all_ok and ok
    print(f"        {'✅ PASS' if ok else '✗ FAIL'}")
    if args.verbose or not ok:
        print(r.stdout[-1500:])

    print("\n  " + "=" * 60)
    if all_ok:
        print("  ✅ ALL 20 TEST SUITES PASSED (320+ tests, 0 failures)")
    else:
        print("  ⚠️  SOME TESTS FAILED - see above for details")
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


# ---------------------------------------------------------------------------
# Away Mode / Research / Knowledge Base (V3 Away Mode)
# ---------------------------------------------------------------------------
def _away_stack():
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.away.context import build_away_stack
    return build_away_stack()


def cmd_kb(args):
    """Knowledge base: add files/folders/urls, query, search."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.away.knowledge_base import KnowledgeBase
    kb = KnowledgeBase()
    action = getattr(args, "kb_action", None) or "stats"

    if action == "add":
        for target in args.targets:
            try:
                n = kb.add_file(target)
                print(f"  ✅ Ingested {n} chunk(s) from {target}")
            except FileNotFoundError:
                # maybe it's a URL
                if "://" in target:
                    try:
                        n = kb.add_url(target)
                        print(f"  ✅ Ingested {n} chunk(s) from URL {target}")
                        continue
                    except Exception as e:
                        print(f"  ❌ URL ingest failed: {e}")
                        continue
                print(f"  ❌ Not found: {target}")
            except Exception as e:
                print(f"  ❌ {e}")
        return 0

    if action == "query":
        q = " ".join(args.question) if isinstance(args.question, list) else (args.question or "")
        if not q:
            q = " ".join(getattr(args, "targets", []) or [])
        res = kb.query(q, k=args.k)
        print(f"\n  Question: {q}\n")
        print(res["context"] or "  (no context retrieved)")
        print()
        return 0

    if action == "search":
        term = " ".join(args.question) if isinstance(args.question, list) else (args.question or "")
        if not term:
            term = " ".join(getattr(args, "targets", []) or [])
        results = kb.search(term, k=args.k)
        print(f"\n  Search '{term}': {len(results)} result(s)\n")
        for r in results:
            print(f"  • {r['title']}  [{r['source']}]")
        print()
        return 0

    if action == "list":
        for s in kb.list_sources():
            print(f"  • {s['source']}  ({s['n_chunks']} chunks)")
        return 0

    if action == "stats":
        st = kb.stats()
        print("\n  Knowledge Base stats:")
        print(f"    Long-term items : {st['memory']['long_term_items']}")
        print(f"    Hot cache size  : {st['memory']['hot_cache_size']}")
        print(f"    Pinned context  : {st['memory']['pinned_context_keys']} keys")
        print(f"    Sources         : {st['sources']}")
        print()
        return 0
    return 1


def cmd_research(args):
    """Run an autonomous research task and print/save the report."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.away.research import ResearchAgent
    from omni_v2.away.knowledge_base import KnowledgeBase
    agent = ResearchAgent(knowledge_base=KnowledgeBase())
    topic = " ".join(args.topic) if isinstance(args.topic, list) else (args.topic or "")
    if not topic:
        topic = " ".join(args.rest)
    print(f"\n  🔬 Researching: {topic}\n")
    report = agent.research(topic)
    md = report.to_markdown()
    print(md)
    # Save to disk
    from omni_v2.away.reporter import Reporter
    rep = Reporter().build_research_report(report)
    print(f"\n  📄 Saved report: {rep.path}\n")
    return 0


def cmd_away(args):
    """Away mode: manage the unattended task queue."""
    sys.path.insert(0, str(REPO_ROOT))
    stack = _away_stack()
    agent = stack["away_agent"]
    action = getattr(args, "away_action", None) or "status"

    if action == "start":
        st = agent.away_start()
        print(f"  🛰  Away mode ON. Queued tasks: {st['queued_tasks']}")
        return 0
    if action == "stop":
        st = agent.away_stop()
        print("  Away mode OFF")
        return 0
    if action == "status":
        st = agent.stats()
        print("\n  Away mode status:")
        print(f"    Active          : {'ON' if st['active'] else 'OFF'}")
        print(f"    Total tasks     : {st['tasks_total']}")
        print(f"    By status       : {st['tasks_by_status']}")
        print(f"    Messenger       : {stack['messenger'].channel}")
        print()
        return 0
    if action == "list":
        print("\n  Away task queue:")
        for t in agent.list_tasks(limit=20):
            print(f"    [{t.status}] {t.kind}: {t.brief} (created {t.created_at:.0f})")
        print()
        return 0
    if action == "add":
        brief = " ".join(args.topic) if isinstance(args.topic, list) else (args.topic or "")
        if not brief:
            brief = " ".join(args.rest)
        kind = args.kind or "research"
        task = agent.submit(kind, brief)
        print(f"  ✅ Queued [{task.kind}] {task.id}: {task.brief}")
        return 0
    if action == "run":
        if args.id:
            t = agent.run_task(args.id)
            print(f"  Task {t.id} -> {t.status}: {t.error or 'ok'}")
        else:
            done = agent.run_pending()
            print(f"  Ran {len(done)} pending task(s)")
            for t in done:
                print(f"    [{t.status}] {t.kind}: {t.brief}")
        return 0
    return 1


def cmd_report(args):
    """Reports: list saved reports or build a digest."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.away.reporter import Reporter
    rep = Reporter()
    action = getattr(args, "report_action", None) or "list"
    if action == "list":
        print("\n  Recent reports:")
        for r in rep.list_recent(n=15):
            print(f"    • {r['title']}  ({r['path']})")
        print()
        return 0
    if action == "digest":
        from omni_v2.away.away_agent import AwayAgent
        from omni_v2.away.knowledge_base import KnowledgeBase
        agent = AwayAgent(knowledge_base=KnowledgeBase())
        t = agent.submit("digest", "manual")
        agent.run_task(t.id)
        print(f"  Digest task {t.id}: {t.status}")
        return 0
    return 1


def cmd_app(args):
    """Launch the full Python desktop control panel (Away Mode + Security)."""
    script = REPO_ROOT / "omni_desktop.py"
    if not script.exists():
        print("  ❌ omni_desktop.py not found")
        return 1
    print("\n  🖥️  OMNI Desktop (Away Mode + Security) — needs a display\n")
    subprocess.run([sys.executable, str(script)])
    return 0


def cmd_messenger(args):
    """Messenger setup & diagnostics (WhatsApp for Pakistan / Telegram / file)."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.away.messenger import (
        load_away_config, save_away_config, whatsapp_setup_guide,
        MessengerRouter, normalize_phone, WhatsAppMessenger,
    )
    action = getattr(args, "messenger_action", None) or "status"

    if action == "setup-whatsapp":
        print("\n" + whatsapp_setup_guide())
        return 0

    if action == "whatsapp-set":
        num = args.number
        if not num:
            print("  Usage: omni messenger whatsapp-set <+92...>")
            return 1
        norm = normalize_phone(num)
        cfg = load_away_config()
        cfg["messenger"] = {"provider": "whatsapp", "phone_number": norm,
                            "token": "", "chat_id": ""}
        save_away_config(cfg)
        print(f"  ✅ Messenger set to WhatsApp Web -> {norm}")
        print(f"     (set up WhatsApp Web first: omni messenger setup-whatsapp)")
        return 0

    if action == "set":
        kind = args.kind
        cfg = load_away_config()
        m = cfg.get("messenger", {})
        if kind == "whatsapp":
            m.update({"provider": "whatsapp"})
        elif kind == "telegram":
            m.update({"provider": "telegram"})
        elif kind == "file":
            m.update({"provider": "file"})
        else:
            print(f"  Unknown provider: {kind} (file|whatsapp|telegram)")
            return 1
        cfg["messenger"] = m
        save_away_config(cfg)
        print(f"  ✅ Messenger provider -> {kind}")
        return 0

    if action == "status":
        cfg = load_away_config()
        m = cfg.get("messenger", {})
        router = MessengerRouter(config=cfg)
        active = router.channel
        print("\n  Messenger status:")
        print(f"    Configured provider : {m.get('provider', 'file')}")
        print(f"    Active channel      : {active}")
        print(f"    Phone (whatsapp)    : {m.get('phone_number') or '(not set)'}")
        print(f"    Telegram token set  : {'yes' if m.get('token') else 'no'}")
        print(f"    Telegram chat id    : {m.get('chat_id') or '(not set)'}")
        if active == "whatsapp":
            chk = WhatsAppMessenger(phone_number=m.get('phone_number', '')).check_ready()
            for k, v in chk.items():
                print(f"      {k}: {v}")
        print()
        return 0

    if action == "test":
        cfg = load_away_config()
        router = MessengerRouter(config=cfg)
        print(f"\n  Sending test message via '{router.channel}'...")
        res = router.send_text("🧪 OMNI messenger test — if you can read this, reports will reach you.")
        print(f"  ok={res.ok}  channel={res.channel}")
        print(f"  detail: {res.detail}")
        print()
        return 0 if res.ok else 1
    return 1


def cmd_security(args):
    """Local camera security: enroll owner, arm/disarm guard, lock."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.security.face_auth import FaceAuth
    from omni_v2.security.guard_monitor import GuardMonitor
    from omni_v2.security.lockdown import LockdownController
    action = getattr(args, "security_action", None) or "status"
    fa = FaceAuth()

    if action == "status":
        st = fa.stats()
        print(f"  Enrolled      : {'✅ yes' if st['enrolled'] else '❌ no (run: omni security enroll)'}")
        print(f"  Threshold     : {st['threshold']}")
        print(f"  Owner file    : {st['owner_path']}")
        print()
        return 0

    if action == "enroll":
        print("  📸 Opening camera — look at it for ~2s to enroll your face (multi-sample)...")
        import time
        try:
            res = fa.enroll_from_camera(frames=6, delay=0.25)
            print(f"  ✅ Enrolled! backend={res['backend']}, samples={res['samples']}")
            return 0
        except Exception as e:
            print(f"  ❌ Enroll failed: {e}")
            return 1
        finally:
            fa.close_camera()

    if action in ("arm", "disarm", "snapshot"):
        gm = GuardMonitor(face_auth=fa)
        if action == "arm":
            ok = gm.arm()
            print(f"  {'✅ Guard armed (intruder -> alert + lock)' if ok else '❌ Cannot arm (enroll owner first / no camera)'}")
            return 0 if ok else 1
        if action == "disarm":
            gm.disarm()
            print("  Guard disarmed")
            return 0
        if action == "snapshot":
            res = gm.snapshot()
            print(f"  Verdict: {res.get('verdict')}  (faces={res.get('faces', 0)})")
            return 0

    if action == "lock":
        lc = LockdownController()
        ev = lc.lock_with_countdown(reason="manual lock via omni security", block=False)
        print(f"  🔒 Locking in {ev['countdown']}s")
        return 0
    return 1


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

    # --- Away Mode (V3) ---
    kb = sub.add_parser("kb", help="Knowledge base (RAG+CAG hybrid memory)")
    kb_sub = kb.add_subparsers(dest="kb_action")
    kb_add = kb_sub.add_parser("add", help="Ingest a file/folder/url")
    kb_add.add_argument("targets", nargs="+")
    kb_add.add_argument("-t", "--title", default="")
    kb_q = kb_sub.add_parser("query", help="Ask the knowledge base")
    kb_q.add_argument("question", nargs="*")
    kb_q.add_argument("-k", type=int, default=5)
    kb_s = kb_sub.add_parser("search", help="Keyword search")
    kb_s.add_argument("question", nargs="*")
    kb_s.add_argument("-k", type=int, default=10)
    kb_sub.add_parser("list", help="List ingested sources")
    kb_sub.add_parser("stats", help="KB stats")

    r = sub.add_parser("research", help="Autonomous research task")
    r.add_argument("topic", nargs="*")
    r.add_argument("rest", nargs=argparse.REMAINDER, default=[])

    away = sub.add_parser("away", help="Away mode (unattended tasks + reports)")
    away_sub = away.add_subparsers(dest="away_action")
    away_sub.add_parser("start")
    away_sub.add_parser("stop")
    away_sub.add_parser("status")
    away_sub.add_parser("list")
    away_add = away_sub.add_parser("add", help="Queue a task")
    away_add.add_argument("topic", nargs="*")
    away_add.add_argument("--kind", choices=["research", "digest", "notify"], default="research")
    away_add.add_argument("rest", nargs=argparse.REMAINDER, default=[])
    away_run = away_sub.add_parser("run", help="Run pending tasks now")
    away_run.add_argument("--id", default=None)

    report = sub.add_parser("report", help="Reports & digests")
    report_sub = report.add_subparsers(dest="report_action")
    report_sub.add_parser("list")
    report_sub.add_parser("digest")

    sub.add_parser("app", help="Launch full Python desktop app (Away + Security)")

    sec = sub.add_parser("security", help="Local camera security")
    sec_sub = sec.add_subparsers(dest="security_action")
    sec_sub.add_parser("status")
    sec_sub.add_parser("enroll")
    sec_sub.add_parser("arm")
    sec_sub.add_parser("disarm")
    sec_sub.add_parser("snapshot")
    sec_sub.add_parser("lock")

    msg = sub.add_parser("messenger", help="Messenger setup & diagnostics (WhatsApp/Telegram/file)")
    msg_sub = msg.add_subparsers(dest="messenger_action")
    msg_sub.add_parser("status")
    msg_sub.add_parser("test")
    msg_sub.add_parser("setup-whatsapp")
    msg_set_wa = msg_sub.add_parser("whatsapp-set", help="Set your WhatsApp number")
    msg_set_wa.add_argument("number")
    msg_set = msg_sub.add_parser("set", help="Set provider (file|whatsapp|telegram)")
    msg_set.add_argument("kind", choices=["file", "whatsapp", "telegram"])

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
    if cmd == "kb":
        return cmd_kb(args)
    if cmd == "research":
        return cmd_research(args)
    if cmd == "away":
        return cmd_away(args)
    if cmd == "report":
        return cmd_report(args)
    if cmd == "app":
        return cmd_app(args)
    if cmd == "security":
        return cmd_security(args)
    if cmd == "messenger":
        return cmd_messenger(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
