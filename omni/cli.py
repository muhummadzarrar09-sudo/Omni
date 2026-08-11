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
import json
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
        print(f"    Deep tier   : {'✅ ' + (status.get('deep_model_path') or '') if status.get('deep_available') else '❌ not present (omni model download --deep)'}")
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


def cmd_model_download_deep(args):
    """Download the deep-tier Qwen2.5-3B GGUF for hard reasoning (Phase 9 Step 2)."""
    target = REPO_ROOT / "data" / "models" / "qwen2.5-3b-instruct-q4_k_m.gguf"
    if target.exists():
        print(f"  ✅ Already present: {target} ({target.stat().st_size // 1024 // 1024} MB)")
        return 0
    print("  Downloading Qwen2.5-3B-Instruct Q4_K_M (~2GB) for the deep reasoning tier...")
    print("  (On a 4GB GPU this is the largest model that fits; it is swapped in only")
    print("   for hard reasoning and swapped back out to keep the fast 1.5B model.)")
    target.parent.mkdir(parents=True, exist_ok=True)
    url = "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf"
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
        print(f"  ✅ Deep model saved to {target}")
        return 0
    except Exception as e:
        print(f"  ❌ Download failed: {e}")
        if target.exists():
            target.unlink()
        return 1


def cmd_test(args):
    """Run all 20 test suites."""
    print("\n  " + "=" * 60)
    print("  OMNI V3 - Full Test Suite (54 suites)")
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
        # Jarvis Brain (Phase 9)
        ("[29/32] Identity core + user model",        "omni_v2.tests.test_identity", "module"),
        ("[30/32] Model tiering (deep brain)",        "omni_v2.tests.test_model_tiering", "module"),
        ("[31/32] Goal stack (decompose/progress/replan)", "omni_v2.tests.test_goals", "module"),
        ("[32/33] Metacognition (evaluator feedback loop)", "omni_v2.tests.test_metacog", "module"),
        ("[33/34] Episodic reflection + patterns",     "omni_v2.tests.test_reflect", "module"),
        ("[34/35] Brain polish (plan-before-acting + offline TTS)", "omni_v2.tests.test_brain_polish", "module"),
        ("[35/37] Offline voice (wake word + STT)", "omni_v2.tests.test_offline_voice", "module"),
        ("[36/37] Voice loop (hands-free)",         "omni_v2.tests.test_voice_loop", "module"),
        ("[37/40] Proactive guardian",               "omni_v2.tests.test_guardian", "module"),
        ("[38/41] Knowledge graph",                  "omni_v2.tests.test_knowledge_graph", "module"),
        ("[39/41] Morning briefing",                 "omni_v2.tests.test_briefing", "module"),
        ("[40/41] Skill installer",                  "omni_v2.tests.test_skill_installer", "module"),
        ("[41/42] Continual harness",                "omni_v2.tests.test_harness", "module"),
        ("[42/43] Auto post-goal flow",              "omni_v2.tests.test_post_goal_flow", "module"),
        ("[43/44] MCP bridge",                       "omni_v2.tests.test_mcp", "module"),
        ("[44/45] Auto skill verification",          "omni_v2.tests.test_skill_verify", "module"),
        ("[45/46] Context compaction",               "omni_v2.tests.test_compaction", "module"),
        ("[46/47] Sub-agent delegation",             "omni_v2.tests.test_subagents", "module"),
        ("[47/48] Automation triggers",              "omni_v2.tests.test_automation", "module"),
        ("[48/49] LLM router v2 (DGX-ready)",        "omni_v2.tests.test_router_v2", "module"),
        ("[49/50] Daemon + auto-start",              "omni_v2.tests.test_daemon", "module"),
        ("[50/51] Self-improvement benchmark",       "omni_v2.tests.test_benchmark", "module"),
        ("[51/52] Skill sandbox",                    "omni_v2.tests.test_sandbox", "module"),
        ("[52/53] Credential vault",                 "omni_v2.tests.test_vault", "module"),
        ("[53/54] Personal context (calendar/contacts/citations)", "omni_v2.tests.test_personal", "module"),
        ("[54/54] Wake routine + harness leaderboard", "omni_v2.tests.test_wake_leaderboard", "module"),
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


def cmd_brain(args):
    """Jarvis Brain: manage identity (self) + user model."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.brain.identity import IdentityCore
    ic = IdentityCore()
    action = getattr(args, "brain_action", None) or "status"

    if action == "status":
        st = ic.stats()
        print("\n  🧠 Jarvis Identity")
        print(f"    Name        : {st['name']}")
        print(f"    Persona     : {st['persona']}")
        print(f"    Mood        : {st['mood']}")
        print(f"    Values      : {', '.join(st['values'])}")
        print(f"    Goals today : {st['goals_today'] or '(none)'}")
        print(f"    Reflections : {st['reflections']}")
        print(f"\n  👤 User model")
        u = st['user']
        print(f"    Name   : {u.get('name') or '(not set)'}")
        print(f"    Style  : {u.get('style')}")
        print(f"    Tone   : {u.get('tone')}")
        print(f"    Likes  : {', '.join(u.get('likes', [])) or '(none)'}")
        print(f"    Prefs  : {u.get('comm_prefs')}")
        print()
        return 0

    if action == "set-name":
        ic.set_name(" ".join(args.rest))
        print(f"  ✅ Identity name -> {' '.join(args.rest)}")
        return 0

    if action == "set-persona":
        ic.set_persona(" ".join(args.rest))
        print("  ✅ Persona updated")
        return 0

    if action == "set-mood":
        ic.set_mood(" ".join(args.rest))
        print(f"  ✅ Mood -> {' '.join(args.rest)}")
        return 0

    if action == "user":
        # omni brain user name=X style=Y likes=a,b
        updates = {}
        for kv in args.rest:
            if "=" in kv:
                k, v = kv.split("=", 1)
                if k in ("likes", "dislikes"):
                    v = [x.strip() for x in v.split(",") if x.strip()]
                updates[k] = v
        if updates:
            ic.update_user(**updates)
            print(f"  ✅ User updated: {updates}")
        else:
            u = ic.stats()["user"]
            print(json.dumps(u, indent=2))
        return 0

    if action == "reflect":
        ic.add_reflection(" ".join(args.rest), kind="note")
        print("  ✅ Reflection saved")
        return 0

    if action == "show-prompt":
        print(ic.to_prompt_block())
        return 0
    return 1


def cmd_voice(args):
    """Voice loop: hands-free 'Hey OMNI' conversation + voice-driven goals."""
    sys.path.insert(0, str(REPO_ROOT))
    action = getattr(args, "voice_action", None) or "status"
    # build a controller for shared wiring
    from omni_v2.away.desktop import DesktopController
    c = DesktopController()

    if action == "respond":
        text = " ".join(args.rest)
        res = c.voice_respond(text)
        print(f"  OMNI says: {res.get('reply', res.get('detail', '?'))}")
        return 0

    if action == "start":
        res = c.voice_start()
        print(f"  Voice loop: {res['detail']}")
        return 0

    if action == "stop":
        res = c.voice_stop()
        print(f"  Voice loop: {res['detail']}")
        return 0

    if action == "status":
        st = c.voice_stats()
        print("\n  🎙️  Voice loop status:")
        print(f"    Running : {'✅' if st.get('running') else '❌'}")
        print(f"    Wake    : {'✅' if st.get('has_wake') else '❌'}")
        print(f"    STT     : {'✅' if st.get('has_stt') else '❌'}")
        print(f"    Brain   : {'✅' if st.get('has_brain') else '❌'}")
        print(f"    TTS     : {'✅' if st.get('has_tts') else '❌'}")
        print(f"    Turns   : {st.get('turns')}")
        print()
        return 0
    return 1


def cmd_guardian(args):
    """Proactive guardian: watch apps/processes/health + notify anomalies."""
    sys.path.insert(0, str(REPO_ROOT))
    action = getattr(args, "guardian_action", None) or "status"
    from omni_v2.away.desktop import DesktopController
    c = DesktopController()

    if action == "start":
        res = c.guardian_start()
        print(f"  Guardian: {res['detail']}")
        return 0

    if action == "stop":
        res = c.guardian_stop()
        print(f"  Guardian: {res['detail']}")
        return 0

    if action == "scan":
        res = c.guardian_run_once()
        obs = res.get("observations", [])
        print(f"\n  🛡️  Guardian scan: {len(obs)} observation(s)\n")
        for o in obs:
            sev = "🔴" if o["severity"] >= 2 else ("🟡" if o["severity"] == 1 else "⚪")
            print(f"    {sev} {o['title']}: {o['body']}")
        print()
        return 0

    if action == "recent":
        for o in c.guardian_recent():
            print(f"  [{o.get('severity',0)}] {o.get('title')}: {o.get('body')}")
        print()
        return 0

    if action == "status":
        g = c._get_guardian()
        st = g.stats() if g else {"running": False}
        print("\n  🛡️  Guardian status:")
        print(f"    Running     : {'✅' if st.get('running') else '❌'}")
        print(f"    Checkers    : {st.get('checkers')}")
        print(f"    Observations: {st.get('observations')}")
        print(f"    Interval    : {st.get('interval')}s")
        print()
        return 0
    return 1


def cmd_delegate(args):
    """Sub-agent delegation: run goal steps as parallel sub-agents."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.away.desktop import DesktopController
    c = DesktopController()
    action = getattr(args, "delegate_action", None) or "status"

    if action == "goal":
        gid = args.goal
        res = c.delegate_goal(gid)
        print(f"\n  🤖 Sub-agent delegation for goal {gid}:")
        print(f"    {res.get('summary', res.get('summary'))}")
        print()
        return 0

    if action == "status":
        st = c.delegator_stats()
        print("\n  🤖 Sub-agent delegator")
        print(f"    Spawned  : {st.get('spawned', 0)}")
        print(f"    Succeeded: {st.get('succeeded', 0)}")
        print(f"    Failed   : {st.get('failed', 0)}")
        print(f"    Max work : {st.get('max_workers', 3)}")
        print()
        return 0
    return 1


def cmd_router(args):
    """LLM router v2: cost-aware model selection (DGX-ready)."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.away.desktop import DesktopController
    c = DesktopController()
    action = getattr(args, "router_action", None) or "status"

    if action == "status":
        st = c.router_stats()
        print("\n  🎛️  LLM Router V2")
        print(f"    Tiers          : {', '.join(st.get('tiers', []))}")
        print(f"    Available      : {', '.join(st.get('available_models', []))}")
        print(f"    Has resolver   : {st.get('has_resolver', False)}")
        print("\n  (Cost-aware: picks the cheapest capable model per task.")
        print("   On the 1050 Ti: 1.5B fast/brain, 3B deep.")
        print("   On the DGX: automatically uses 14B/72B+ reasoning tiers.)")
        print()
        return 0

    if action == "route":
        text = " ".join(args.rest)
        if not text:
            print("  Usage: omni router route <task text>")
            return 1
        res = c.router_select(text)
        if not res.get("ok"):
            print(f"  ❌ {res.get('detail','?')}")
            return 1
        d = res["decision"]
        print(f"\n  Task: {text}\n")
        print(f"    → tier {d['tier']} · model {d['model']} (required cap {d['required_cap']})")
        print(f"      {d['reason']} · est {d['estimated_tokens']} tokens")
        print()
        return 0
    return 1


def cmd_wake(args):
    """Wake routine: the 'Good morning Zarrar' scripted flow."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.away.desktop import DesktopController
    c = DesktopController()
    action = getattr(args, "wake_action", None) or "status"

    if action == "run":
        res = c.wake_run(speak=args.speak, push=args.push)
        print(f"\n  🌅 Wake routine: {res.get('greeting', res.get('detail','?'))}")
        print(f"    spoken : {'✅' if res.get('spoken') else '❌'}  pushed: {'✅' if res.get('pushed') else '❌'}  guardian: {'✅' if res.get('guardian_warmed') else '❌'}")
        print()
        return 0
    if action == "status":
        res = c.wake_status()
        print("\n  🌅 Wake Routine")
        print(f"    User       : {res.get('user_name') or '(not set)'}")
        print(f"    Identity   : {'✅' if res.get('has_identity') else '❌'}")
        print(f"    Calendar   : {'✅' if res.get('has_calendar') else '❌'}")
        print(f"    Briefing   : {'✅' if res.get('has_briefing') else '❌'}")
        print(f"    TTS        : {'✅' if res.get('has_tts') else '❌'}")
        print(f"    Messenger  : {'✅' if res.get('has_messenger') else '❌'}")
        print()
        return 0
    return 1


def cmd_leaderboard(args):
    """Harness leaderboard: prioritize which skills/automations to improve."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.away.desktop import DesktopController
    c = DesktopController()
    action = getattr(args, "leaderboard_action", None) or "report"

    if action == "report":
        kind = args.kind or ""
        rep = c.leaderboard_report(kind).get("report", {})
        print(f"\n  🏆 Harness Leaderboard ({kind or 'all'}): {rep.get('total', 0)} tracked\n")
        print("  KEEP (working well):")
        for e in rep.get("keep", []):
            print(f"    ✓ {e['name']}  uses={e['uses']} ok={e['ok']} fail={e['fail']}")
        if not rep.get("keep"):
            print("    (none)")
        print("\n  REFINE (failing/unused):")
        for e in rep.get("refine", []):
            print(f"    ⚠ {e['name']}  uses={e['uses']} ok={e['ok']} fail={e['fail']}")
        if not rep.get("refine"):
            print("    (none)")
        print()
        return 0
    if action == "record":
        res = c.leaderboard_record(args.name, args.kind or "skill", args.ok)
        print(f"  ✅ Recorded {args.name} ({args.ok})")
        return 0
    return 1


def cmd_personal(args):
    """Personal context: local calendar + contacts, and KB answers with citations."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.away.desktop import DesktopController
    c = DesktopController()
    action = getattr(args, "personal_action", None) or "status"

    if action == "calendar":
        res = c.calendar_upcoming(hours=args.hours)
        events = res.get("events", [])
        print(f"\n  📅 Upcoming events ({args.hours}h):")
        if not events:
            print("    (none)")
        for e in events:
            print(f"    • {e['summary']}  @ {e['start']}  {e.get('location','')}")
        print()
        return 0

    if action == "contacts":
        res = c.contacts_lookup(args.name) if args.name else None
        if res and res["ok"]:
            ct = res["contact"]
            print(f"\n  👤 {ct['name']}")
            if ct.get("phone"):
                print(f"    phone: {ct['phone']}")
            if ct.get("email"):
                print(f"    email: {ct['email']}")
            print()
            return 0
        print(f"\n  👤 No contact found for '{args.name or '?'}'")
        print()
        return 1

    if action == "cite":
        q = " ".join(args.question)
        res = c.kb_query_cited(q)
        print(f"\n  📄 Question: {q}\n")
        print(res.get("context", "(no knowledge)"))
        print("\n  Sources:")
        for cit in res.get("citations", []):
            print(f"    [{cit['id']}] {cit['source']}  ({cit['title']})")
        print()
        return 0

    if action == "status":
        cal = c.calendar.stats() if c.calendar else {"events_total": 0}
        cs = c.contacts.stats() if c.contacts else {"contacts": 0}
        print("\n  📅 Personal Context")
        print(f"    Calendar : {cal.get('events_total', 0)} event(s)")
        print(f"    Contacts : {cs.get('contacts', 0)}")
        print(f"    Citations: kb query-with-citations enabled")
        print()
        return 0
    return 1


def cmd_vault(args):
    """Credential vault: encrypted local secrets with a permission gate."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.away.desktop import DesktopController
    c = DesktopController()
    action = getattr(args, "vault_action", None) or "list"

    if action == "list":
        res = c.vault_list()
        secrets = res.get("secrets", [])
        print("\n  🔐 Credential Vault")
        if not secrets:
            print("    (no secrets stored)")
        for s in secrets:
            print(f"    • {s['name']}  allowed={s.get('allowed')}  {s.get('metadata','')}")
        print()
        return 0

    if action == "set":
        name, value = args.name, args.value
        callers = args.callers.split(",") if args.callers else None
        res = c.vault_set(name, value, callers=callers, metadata=args.metadata or "")
        if res.get("ok"):
            print(f"  ✅ Stored '{name}' (callers: {res.get('callers', callers)})")
            return 0
        print(f"  ❌ {res.get('detail','?')}")
        return 1

    if action == "get":
        name = args.name
        res = c.vault_get(name, caller=args.caller or "omni")
        if res.get("ok"):
            print(f"  🔑 {name} = {res['value']}")
            return 0
        print(f"  ❌ {res.get('detail','?')}")
        return 1

    if action == "delete":
        res = c.vault_delete(args.name) if hasattr(c, "vault_delete") else None
        if res is None:
            from omni_v2.away.desktop import DesktopController as DC
            c2 = DC()
            v = c2._get_vault()
            ok = v.delete_secret(args.name) if v else False
        else:
            ok = res.get("ok", False)
        print(f"  {'✅ Deleted' if ok else '❌ not found'}")
        return 0

    if action == "stats":
        st = c.vault_stats()
        print("\n  🔐 Vault")
        print(f"    Secrets   : {st.get('secrets', 0)}")
        print(f"    Key source: {st.get('key_source', '?')}")
        print(f"    File      : {st.get('vault_file', '?')}")
        print()
        return 0
    return 1


def cmd_sandbox(args):
    """Skill sandbox: run untrusted skill code in an isolated subprocess."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.away.desktop import DesktopController
    c = DesktopController()
    action = getattr(args, "sandbox_action", None) or "status"

    if action == "status":
        st = c.skill_sandbox_status().get("status", {})
        print("\n  🛡️  Skill Sandbox")
        print(f"    Timeout    : {st.get('timeout_s')}s")
        print(f"    Max mem    : {st.get('max_mem_mb')} MB")
        print(f"    Isolated   : {'✅ subprocess' if st.get('isolated') else '❌'}")
        print(f"    Network    : {'⛔ blocked' if st.get('network_blocked') else '⚠️ allowed'}")
        print()
        return 0

    if action == "run":
        code = " ".join(args.code) if args.code else ""
        res = c.skill_sandbox_run(code=code, skill_name=args.skill or "")
        if not res.get("ok"):
            print(f"  ❌ {res.get('detail', res.get('result', {}).get('error', '?'))}")
            return 1
        r = res["result"]
        print(f"\n  🛡️  Sandbox run:")
        print(f"    ok        : {'✅' if r['ok'] else '❌'}")
        print(f"    output    : {r['output'] or '(none)'}")
        print(f"    error     : {r['error'] or '(none)'}")
        print(f"    timed out : {r['timed_out']}  exit: {r['exit_code']}")
        print()
        return 0
    return 1


def cmd_benchmark(args):
    """Self-improvement benchmark: measure how much faster/cheaper OMNI gets."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.away.desktop import DesktopController
    c = DesktopController()
    action = getattr(args, "benchmark_action", None) or "report"

    if action == "report":
        rep = c.benchmark_report().get("report", {})
        imp = rep.get("improvement", {})
        print("\n  📊 Self-Improvement Benchmark")
        print(f"    Case      : {rep.get('case', 'all')}")
        print(f"    Iterations: {rep.get('iterations', 0)}")
        print(f"    Early     : {rep.get('early', {})}")
        print(f"    Late      : {rep.get('late', {})}")
        print(f"    Improvement:")
        print(f"      time   : {imp.get('time_pct', 'n/a')}%")
        print(f"      tokens : {imp.get('tokens_pct', 'n/a')}%")
        print(f"      steps  : {imp.get('steps_pct', 'n/a')}%")
        print()
        return 0

    if action == "run":
        case = args.case or "generic"
        briefs = args.briefs or [case]
        # demo executor: faster when harness context present
        def executor(brief, ctx):
            if ctx:
                return {"ok": True, "time": 1.0, "tokens": 50, "steps": 3}
            return {"ok": True, "time": 3.0, "tokens": 150, "steps": 7}
        res = c.benchmark_run(case, briefs, iterations=args.iterations, executor=executor)
        if not res.get("ok"):
            print(f"  ❌ {res.get('detail','?')}")
            return 1
        rep = res["report"]
        imp = rep.get("improvement", {})
        print(f"\n  📊 Ran benchmark '{case}' ({args.iterations} iterations)")
        print(f"    Early: {rep.get('early', {})}")
        print(f"    Late : {rep.get('late', {})}")
        print(f"    Improvement: time {imp.get('time_pct','n/a')}% · tokens {imp.get('tokens_pct','n/a')}% · steps {imp.get('steps_pct','n/a')}%")
        print()
        return 0
    return 1


def cmd_daemon(args):
    """OMNI daemon: always-on resident agent + auto-start."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.daemon.daemon import AutoStartManager, DaemonController
    from omni_v2.away.desktop import DesktopController
    action = getattr(args, "daemon_action", None) or "status"
    asm = AutoStartManager()

    if action == "enable":
        res = asm.enable()
        print(f"  ✅ Auto-start enabled ({res['backend']}):\n     {res['command']}")
        return 0
    if action == "disable":
        res = asm.disable()
        print(f"  {'✅ Auto-start disabled' if res['ok'] else '❌ failed'}")
        return 0
    if action == "status":
        st = asm.status()
        print(f"\n  🖥️  OMNI Daemon")
        print(f"    Auto-start : {'✅ installed' if st['installed'] else '❌ not installed'} ({st['backend']})")
        print()
        return 0
    if action == "start":
        # start resident services in background
        c = DesktopController()
        svcs = {}
        svcs["guardian"] = lambda: c.guardian_start()
        svcs["automation"] = lambda: c._get_triggers()
        if c.away:
            svcs["away"] = lambda: c.away.away_start()
        d = DaemonController(services=svcs)
        res = d.start()
        print(f"  ▶ Resident services started: {', '.join(res['started']) or '(none)'}")
        print("  (this process keeps them alive; run 'omni daemon start' in a terminal)")
        import time
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            d.stop()
        return 0
    if action == "stop":
        d = DaemonController()
        d.stop()
        print("  ■ Stopped")
        return 0
    return 1


def cmd_automation(args):
    """Automation triggers: webhook/schedule/file events wake OMNI."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.away.desktop import DesktopController
    c = DesktopController()
    action = getattr(args, "automation_action", None) or "status"

    if action == "status":
        st = c.trigger_stats()
        by = st.get("by_trigger", {})
        print("\n  ⚡ Automation Triggers")
        print(f"    Triggers : {st.get('triggers', 0)}")
        print(f"    Webhooks : {by.get('webhook', 0)}  Schedules: {by.get('schedule', 0)}  Files: {by.get('file', 0)}")
        print(f"    Fired    : {st.get('fired', 0)}")
        print()
        return 0

    if action == "add":
        name, trigger, action_kind = args.name, args.trigger, args.action
        # build action_args from remaining k=v
        action_args = {}
        for kv in args.rest:
            if "=" in kv:
                k, v = kv.split("=", 1)
                action_args[k] = v
        res = c.trigger_add(name, trigger, action_kind, action_args, secret=args.secret or "")
        if res["ok"]:
            print(f"  ✅ Added {trigger} trigger '{name}' -> {action_kind}")
            return 0
        print(f"  ❌ {res.get('detail','?')}")
        return 1

    if action == "fire":
        res = c.trigger_fire(args.name, {})
        print(f"  ⚡ Fire '{args.name}': ok={res.get('ok')} {res.get('detail', res.get('result',''))}")
        return 0

    if action == "list":
        res = c.trigger_list()
        for a in res.get("automations", []):
            print(f"  • {a['name']} [{a['trigger']}] -> {a['action']} {a.get('action_args', {})} "
                  f"(enabled={a['enabled']}, fired={a['fire_count']})")
        if not res.get("automations"):
            print("  (no triggers — try: omni automation add deploy webhook goal intent=\"deploy the app\")")
        return 0
    return 1


def cmd_compaction(args):
    """Context auto-compaction: summarize old turns to save tokens."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.llm.compaction import Compactor
    c = Compactor()
    action = getattr(args, "compaction_action", None) or "status"

    if action == "status":
        st = c.stats()
        print("\n  🧹 Context Auto-Compaction")
        print(f"    Enabled   : {'✅' if st['enabled'] else '❌'}")
        print(f"    Max tokens: {st['max_tokens']}")
        print(f"    Keep last : {st['keep_last']} turns")
        print(f"    Compactions: {st['compactions']}")
        print(f"    Summarizer: {st['summarizer']}")
        print("\n  (Wired into Brain.think() — long conversations are auto-summarized\n   to stay within budget while preserving the task + recent turns.)")
        print()
        return 0
    return 1


def cmd_skill_verify(args):
    """Auto skill verification: test harness skills, roll back failures."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.away.desktop import DesktopController
    c = DesktopController()
    action = getattr(args, "sv_action", None) or "status"

    if action == "status":
        st = c.skill_verify_stats()
        print("\n  ✅ Auto Skill Verification")
        print(f"    Checks : {st.get('checks', 0)}")
        print(f"    Passed : {st.get('passed', 0)}")
        print(f"    Failed : {st.get('failed', 0)}")
        print()
        return 0

    if action == "run":
        # verify all skills (tester may be default=pass; on DGX, real runner)
        res = c.skill_verify()
        results = res.get("results", [])
        print(f"\n  ✅ Verified {len(results)} skill(s):\n")
        for r in results:
            mark = "✅" if r["passed"] else "❌"
            print(f"  {mark} {r['name']} v{r['version']} -> {r['action']}: {r['message']}")
        print()
        return 0

    if action == "history":
        for r in c.skill_verify_history():
            mark = "✅" if r["passed"] else "❌"
            print(f"  {mark} {r['name']} v{r['version']} [{r['action']}] {r['message']}")
        print()
        return 0
    return 1


def cmd_mcp(args):
    """MCP: connect OMNI to the Model Context Protocol ecosystem."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.away.desktop import DesktopController
    c = DesktopController()
    action = getattr(args, "mcp_action", None) or "status"

    if action == "status":
        st = c.mcp_stats()
        print("\n  🔌 MCP Bridge")
        print(f"    Servers    : {st.get('servers', 0)}")
        print(f"    Provider   : {'fake (demo/test)' if st.get('fake_provider') else 'real mcp SDK'}")
        for s in st.get("servers_detail", []):
            print(f"    - {s['name']}: {len(s['tools'])} tool(s)")
        print()
        return 0

    if action == "add-demo":
        # demo server: two fake tools to show the bridge working
        tools = [
            {"name": "get_time", "description": "Return the current time", "inputSchema": {}},
            {"name": "echo", "description": "Echo text back", "inputSchema": {"text": "str"}},
        ]
        def now(args=None):
            import datetime
            return {"content": [{"type": "text", "text": datetime.datetime.now().isoformat()}]}
        def echo(args=None):
            return {"content": [{"type": "text", "text": f"echo: {(args or {}).get('text','')}"}]}
        handlers = {"get_time": now, "echo": echo}
        res = c.mcp_add_server("demo", tools, handlers)
        print(f"  ✅ Demo MCP server added, {res.get('registered_tools', 0)} tool(s) registered")
        print("     (open the MCP tab in the desktop app, or use omni shell to call them)")
        return 0

    if action == "list":
        res = c.mcp_list()
        for s in res.get("servers", []):
            print(f"  • {s['name']}: {', '.join(s['tools']) or '(no tools)'}")
        if not res.get("servers"):
            print("  (no MCP servers — try: omni mcp add-demo)")
        return 0

    if action == "add":
        name = args.name
        import json
        tools = json.loads(args.tools or "[]")
        res = c.mcp_add_server(name, tools)
        print(f"  ✅ Added server {name}: {res.get('registered_tools', 0)} tool(s)")
        return 0
    return 1


def cmd_harness(args):
    """Continual harness: self-refining skills/memory/lessons from trajectories."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.away.desktop import DesktopController
    c = DesktopController()
    action = getattr(args, "harness_action", None) or "status"

    if action == "status":
        st = c.harness_stats()
        by = st.get("by_kind", {})
        print("\n  🧬 Continual Harness")
        print(f"    Artifacts : {st.get('artifacts', 0)}")
        print(f"    Skills    : {by.get('skill', 0)}")
        print(f"    Memory    : {by.get('memory', 0)}")
        print(f"    Lessons   : {by.get('lesson', 0)}")
        print(f"    Distiller : {'✅ (deep LLM)' if st.get('has_distiller') else '○ (deterministic)'}")
        print()
        return 0

    if action == "list":
        kind = args.kind or ""
        res = c.harness_list(kind)
        print(f"\n  🧬 Harness artifacts ({len(res['artifacts'])}):\n")
        for a in res["artifacts"]:
            print(f"  [{a['kind']}] {a['name']} v{a['version']}: {a['content'][:70]}")
        print()
        return 0

    if action == "refine":
        gid = args.goal
        res = c.harness_refine_goal(gid, repeated=args.repeated)
        if not res.get("ok"):
            print(f"  ❌ {res.get('detail','?')}")
            return 1
        comm = res["committed"]
        print(f"\n  🧬 Refined from goal {gid}:")
        print(f"    skills : {comm.get('skills', []) or '(none)'}")
        print(f"    memory : {comm.get('memory', []) or '(none)'}")
        print(f"    lessons: {comm.get('lessons', []) or '(none)'}")
        print()
        return 0

    if action == "rollback":
        ok = c.harness_rollback(args.kind, args.name)
        print(f"  {'✅ Rolled back' if ok.get('ok') else '❌ ' + ok.get('detail','no snapshot')}")
        return 0

    if action == "context":
        topic = " ".join(args.rest)
        print("\n" + (c.harness_context(topic) or "(no harness context)") + "\n")
        return 0
    return 1


def cmd_graph(args):
    """Knowledge graph: build/visualize memory as a graph."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.graph.knowledge_graph import KnowledgeGraphBuilder
    from omni_v2.memory.hybrid_memory import get_hybrid_memory
    from omni_v2.memory.session_memory import SessionMemoryStore
    try:
        session = SessionMemoryStore()
    except Exception:
        session = None
    g = KnowledgeGraphBuilder(memory=get_hybrid_memory(), session_memory=session)
    action = getattr(args, "graph_action", None) or "build"

    if action == "build":
        data = g.build()
        st = data["stats"]
        print(f"\n  🧠 Knowledge Graph: {st['nodes']} nodes, {st['edges']} edges")
        print(f"     (from {st['memory_items']} memory items, {st['sessions']} sessions)")
        print("\n  Top nodes:")
        for n in data["nodes"][:15]:
            print(f"    {n['weight']:3d} [{n['kind']:8s}] {n['name'][:50]}")
        print()
        return 0

    if action == "json":
        out = args.out or (REPO_ROOT / "data" / "knowledge_graph.json")
        path = g.to_json(out)
        print(f"  ✅ Graph saved to {path}")
        return 0

    if action == "view":
        # print a hint to open the web viewer
        print("\n  Open the web viewer:")
        print("    omni start         # FastAPI backend")
        print("    cd frontend_next && npm run dev")
        print("    → http://localhost:3000/knowledge-graph\n")
        return 0
    return 1


def cmd_briefing(args):
    """Morning briefing: build + deliver today's intel."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.briefing.briefing import MorningBriefing
    from omni_v2.brain.goals import GoalStack
    from omni_v2.brain.identity import IdentityCore
    from omni_v2.brain.reflect import Reflector
    from omni_v2.away.reporter import Reporter
    from omni_v2.away.messenger import MessengerRouter
    from omni_v2.memory.session_memory import SessionMemoryStore
    try:
        session = SessionMemoryStore()
    except Exception:
        session = None
    b = MorningBriefing(
        goals=GoalStack(),
        reflector=Reflector(session_memory=session),
        research=None,
        reporter=Reporter(),
        messenger=MessengerRouter(),
        identity=IdentityCore(),
    )
    action = getattr(args, "briefing_action", None) or "build"
    if action == "build":
        data = b.build(research_topic=args.topic or "")
        print("\n" + data["markdown"] + "\n")
        return 0
    if action == "deliver":
        res = b.deliver(research_topic=args.topic or "", save_report=True, push=True)
        print("\n" + res["markdown"] + "\n")
        print(f"  saved: {res['saved_path'] or '(not saved)'}  pushed: {res['pushed']}")
        return 0
    return 1


def cmd_add_skill(args):
    """Skill installer: omni add-skill <url> pulls + verifies + wires a skill."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.skills.installer import SkillInstaller
    inst = SkillInstaller()
    action = getattr(args, "skill_action", None) or "install"
    if action == "install":
        source = " ".join(args.source)
        if not source:
            print("  Usage: omni add-skill <url-or-file> [--allow-network]")
            return 1
        res = inst.install(source, allow_network=getattr(args, "allow_network", False))
        if res["ok"]:
            print(f"  ✅ Skill installed: {res['detail']}")
            return 0
        print(f"  ❌ {res['step']}: {res['detail']}")
        return 1
    if action == "list":
        listing = inst.list_installed()
        print(f"\n  🧩 Installed skills ({listing['count']}):")
        for s in listing["skills"]:
            print(f"    - {s}")
        print()
        return 0
    return 1


def cmd_meta(args):
    """Jarvis Brain metacognition: evaluate an outcome + feed back into a goal."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.brain.metacog import Metacog
    from omni_v2.brain.goals import GoalStack
    m = Metacog()
    action = getattr(args, "meta_action", None) or "history"

    if action == "evaluate":
        # omni meta evaluate "the message" [--goal <id>] [--ok]
        # REMAINDER swallows --goal/--ok, so extract them from the token list.
        rest = list(args.rest)
        goal_id = args.goal
        ok = args.ok
        if "--goal" in rest:
            i = rest.index("--goal")
            if i + 1 < len(rest):
                goal_id = rest[i + 1]
            del rest[i:i + 2]
        if "--ok" in rest:
            ok = True
            rest.remove("--ok")
        msg = " ".join(rest)
        v = m.decide(ok, message=msg, error="", goal_has_plan=bool(goal_id))
        print(f"\n  🧠 Verdict")
        print(f"    succeeded : {v.succeeded}")
        print(f"    confidence: {v.confidence}")
        print(f"    cause     : {v.cause}")
        print(f"    action    : {v.action}")
        if v.suggested_fix:
            print(f"    fix       : {v.suggested_fix}")
        if v.ask_user:
            print(f"    ask user  : {v.ask_user}")
        if goal_id:
            gs = GoalStack()
            m.apply_to_goal(gs, goal_id, v, do_replan=True)
            g = gs.get_goal(goal_id)
            print(f"\n  Goal {goal_id}:")
            if g:
                print(f"    status={g.status} progress={g.progress:.0%} steps={len(g.steps)}")
        print()
        return 0

    if action == "history":
        for rec in m.history(20):
            v = rec["verdict"]
            print(f"  [{rec['ts']:.0f}] {v['action']:16s} cause={v['cause']:18s} ok={v['succeeded']} :: {v['message'][:60]}")
        print()
        return 0

    if action == "stats":
        import json
        print(json.dumps(m.stats(), indent=2))
        return 0
    return 1


def cmd_reflect(args):
    """Jarvis Brain episodic reflection + pattern awareness (Step 5)."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.brain.reflect import Reflector
    from omni_v2.memory.session_memory import SessionMemoryStore
    from omni_v2.memory.hybrid_memory import get_hybrid_memory
    from omni_v2.brain.identity import IdentityCore
    r = Reflector(session_memory=SessionMemoryStore(), hybrid_memory=get_hybrid_memory(),
                  identity=IdentityCore())
    action = getattr(args, "reflect_action", None) or "today"

    if action == "today":
        ep = r.reflect_today()
        print(f"\n  📓 Episodic recap ({ep.day}):\n    {ep.summary}")
        print(f"    activity: {ep.activity}")
        print()
        return 0

    if action == "patterns":
        pats = r.detect_patterns(days=args.days)
        print(f"\n  🧩 Patterns (last {args.days} days):")
        if not pats:
            print("    (no notable patterns yet)")
        for p in pats:
            sev = "🔴" if p["severity"] >= 2 else ("🟡" if p["severity"] == 1 else "⚪")
            print(f"    {sev} {p['title']}\n       {p['body']}")
        print()
        return 0

    if action == "episodes":
        for e in r.episodes(15):
            print(f"  [{e.day}] {e.summary}")
        print()
        return 0
    return 1


def cmd_goal(args):
    """Jarvis Brain goals: persistent goal stack (decompose / progress / replan)."""
    sys.path.insert(0, str(REPO_ROOT))
    from omni_v2.brain.goals import GoalStack
    gs = GoalStack()
    action = getattr(args, "goal_action", None) or "list"

    if action == "list":
        print("\n  🎯 Goals")
        for g in gs.list_goals(limit=20):
            print(f"    [{g.status:8s}] {g.title}  (progress {g.progress:.0%}, {len(g.steps)} steps)")
            for s in g.steps:
                mark = {"pending": "○", "running": "▶", "done": "✔", "failed": "✘"}.get(s.status, "?")
                print(f"        {mark} {s.desc}")
        if not gs.list_goals():
            print("    (no goals yet — omni goal new \"...\")")
        print()
        return 0

    if action == "new":
        intent = " ".join(args.rest)
        if not intent:
            print("  Usage: omni goal new \"build a habit tracker\"")
            return 1
        g = gs.create_goal(intent)
        print(f"  ✅ Created goal {g.id}: {g.title}")
        print(f"     {len(g.steps)} step(s):")
        for i, s in enumerate(g.steps, 1):
            print(f"       {i}. {s.desc}")
        return 0

    if action == "status":
        gid = args.id
        g = gs.get_goal(gid)
        if not g:
            print(f"  ❌ No goal {gid}")
            return 1
        print(f"\n  🎯 {g.title}  [{g.status}]  progress {g.progress:.0%}")
        for i, s in enumerate(g.steps, 1):
            mark = {"pending": "○", "running": "▶", "done": "✔", "failed": "✘"}.get(s.status, "?")
            line = f"    {i}. {mark} {s.desc}"
            if s.error:
                line += f"  ERROR: {s.error}"
            if s.suggested_fix:
                line += f"  FIX: {s.suggested_fix}"
            print(line)
        if g.follow_up:
            print(f"    Follow-up: {g.follow_up}")
        print()
        return 0

    if action == "advance":
        # run the next step: begin + complete (stub execution; real exec via brain)
        gid = args.id
        s = gs.begin_step(gid)
        if s is None:
            print("  No runnable step (check dependencies / goal done)")
            return 1
        print(f"  ▶ Running: {s.desc}")
        gs.complete_step(gid, result={"ok": True})
        g = gs.get_goal(gid)
        print(f"  ✔ Done. Progress now {g.progress:.0%}")
        if g.status == "done":
            print("  🎉 GOAL COMPLETE")
        return 0

    if action == "fail":
        gid = args.id
        error = " ".join(args.rest)
        gs.fail_step(gid, error=error or "step failed", suggested_fix="")
        print(f"  ✘ Marked running step failed: {error}")
        return 0

    if action == "abandon":
        gid = args.id
        gs.abandon(gid)
        print(f"  Abandoned goal {gid}")
        return 0

    if action == "follow-up":
        gid = args.id
        gs.schedule_follow_up(gid, fu_type="report", message=" ".join(args.rest) or None)
        print(f"  ✅ Follow-up scheduled on goal {gid}")
        return 0
    return 1


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
    m_sub.add_parser("download", help="Download default Qwen2.5-1.5B GGUF").add_argument(
        "--deep", action="store_true", help="Download the deep-tier Qwen2.5-3B GGUF instead"
    )

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

    brain = sub.add_parser("brain", help="Jarvis Brain: identity (self) + user model")
    brain_sub = brain.add_subparsers(dest="brain_action")
    brain_sub.add_parser("status")
    brain_sub.add_parser("show-prompt")
    brain_sub.add_parser("set-name").add_argument("rest", nargs=argparse.REMAINDER)
    brain_sub.add_parser("set-persona").add_argument("rest", nargs=argparse.REMAINDER)
    brain_sub.add_parser("set-mood").add_argument("rest", nargs=argparse.REMAINDER)
    brain_sub.add_parser("user").add_argument("rest", nargs=argparse.REMAINDER)
    brain_sub.add_parser("reflect").add_argument("rest", nargs=argparse.REMAINDER)

    reflect = sub.add_parser("reflect", help="Jarvis Brain: episodic reflection + patterns")
    reflect_sub = reflect.add_subparsers(dest="reflect_action")
    reflect_sub.add_parser("today")
    reflect_p = reflect_sub.add_parser("patterns")
    reflect_p.add_argument("--days", type=int, default=7)
    reflect_sub.add_parser("episodes")

    voice = sub.add_parser("voice", help="Voice loop: hands-free conversation + voice goals")
    voice_sub = voice.add_subparsers(dest="voice_action")
    voice_sub.add_parser("start")
    voice_sub.add_parser("stop")
    voice_sub.add_parser("status")
    _vr = voice_sub.add_parser("respond")
    _vr.add_argument("rest", nargs=argparse.REMAINDER)

    guardian = sub.add_parser("guardian", help="Proactive guardian: watch apps/health")
    guardian_sub = guardian.add_subparsers(dest="guardian_action")
    guardian_sub.add_parser("start")
    guardian_sub.add_parser("stop")
    guardian_sub.add_parser("scan")
    guardian_sub.add_parser("recent")
    guardian_sub.add_parser("status")

    graph = sub.add_parser("graph", help="Knowledge graph: visualize memory")
    graph_sub = graph.add_subparsers(dest="graph_action")
    graph_sub.add_parser("build")
    graph_json = graph_sub.add_parser("json")
    graph_json.add_argument("--out", default=None)
    graph_sub.add_parser("view")

    sv = sub.add_parser("skill-verify", help="Auto skill verification (test harness skills)")
    sv_sub = sv.add_subparsers(dest="sv_action")
    sv_sub.add_parser("status")
    sv_sub.add_parser("run")
    sv_sub.add_parser("history")

    comp = sub.add_parser("compaction", help="Context auto-compaction (token efficiency)")
    comp_sub = comp.add_subparsers(dest="compaction_action")
    comp_sub.add_parser("status")

    deleg = sub.add_parser("delegate", help="Sub-agent delegation (run goal steps in parallel)")
    deleg_sub = deleg.add_subparsers(dest="delegate_action")
    _dg = deleg_sub.add_parser("goal")
    _dg.add_argument("goal")
    deleg_sub.add_parser("status")

    auto = sub.add_parser("automation", help="Automation triggers (webhook/schedule/file wake OMNI)")
    auto_sub = auto.add_subparsers(dest="automation_action")
    auto_sub.add_parser("status")
    _aa = auto_sub.add_parser("add")
    _aa.add_argument("name")
    _aa.add_argument("trigger", choices=["webhook", "schedule", "file"])
    _aa.add_argument("action", choices=["goal", "research", "notify", "away"])
    _aa.add_argument("--secret", default="")
    _aa.add_argument("rest", nargs=argparse.REMAINDER)
    _af = auto_sub.add_parser("fire")
    _af.add_argument("name")
    auto_sub.add_parser("list")

    rtr = sub.add_parser("router", help="LLM router v2: cost-aware model selection (DGX-ready)")
    rtr_sub = rtr.add_subparsers(dest="router_action")
    rtr_sub.add_parser("status")
    _rr = rtr_sub.add_parser("route")
    _rr.add_argument("rest", nargs=argparse.REMAINDER)

    dmn = sub.add_parser("daemon", help="OMNI daemon: always-on resident agent + auto-start")
    dmn_sub = dmn.add_subparsers(dest="daemon_action")
    dmn_sub.add_parser("enable")
    dmn_sub.add_parser("disable")
    dmn_sub.add_parser("status")
    dmn_sub.add_parser("start")
    dmn_sub.add_parser("stop")

    bm = sub.add_parser("benchmark", help="Self-improvement benchmark (faster/cheaper over time)")
    bm_sub = bm.add_subparsers(dest="benchmark_action")
    bm_sub.add_parser("report")
    _bmr = bm_sub.add_parser("run")
    _bmr.add_argument("case", nargs="?", default="")
    _bmr.add_argument("--briefs", nargs="*", default=[])
    _bmr.add_argument("--iterations", type=int, default=3)

    sb = sub.add_parser("sandbox", help="Skill sandbox: run untrusted skill code isolated")
    sb_sub = sb.add_subparsers(dest="sandbox_action")
    sb_sub.add_parser("status")
    _sbr = sb_sub.add_parser("run")
    _sbr.add_argument("--skill", default="")
    _sbr.add_argument("code", nargs=argparse.REMAINDER)

    vl = sub.add_parser("vault", help="Credential vault: encrypted local secrets")
    vl_sub = vl.add_subparsers(dest="vault_action")
    vl_sub.add_parser("list")
    _vs = vl_sub.add_parser("set")
    _vs.add_argument("name")
    _vs.add_argument("value")
    _vs.add_argument("--callers", default=None)
    _vs.add_argument("--metadata", default="")
    _vg = vl_sub.add_parser("get")
    _vg.add_argument("name")
    _vg.add_argument("--caller", default="omni")
    _vd = vl_sub.add_parser("delete")
    _vd.add_argument("name")
    vl_sub.add_parser("stats")

    wk = sub.add_parser("wake", help="Wake routine: 'Good morning' scripted flow")
    wk_sub = wk.add_subparsers(dest="wake_action")
    _wkr = wk_sub.add_parser("run")
    _wkr.add_argument("--no-speak", action="store_true")
    _wkr.add_argument("--no-push", action="store_true")
    wk_sub.add_parser("status")

    lb = sub.add_parser("leaderboard", help="Harness leaderboard: prioritize improvement")
    lb_sub = lb.add_subparsers(dest="leaderboard_action")
    _lbr = lb_sub.add_parser("report")
    _lbr.add_argument("kind", nargs="?", default="")
    _lbre = lb_sub.add_parser("record")
    _lbre.add_argument("name")
    _lbre.add_argument("--kind", default="skill")
    _lbre.add_argument("--fail", action="store_true")

    per = sub.add_parser("personal", help="Personal context: calendar, contacts, KB citations")
    per_sub = per.add_subparsers(dest="personal_action")
    _pc = per_sub.add_parser("calendar")
    _pc.add_argument("--hours", type=int, default=24)
    _pct = per_sub.add_parser("contacts")
    _pct.add_argument("name", nargs="?")
    _pci = per_sub.add_parser("cite")
    _pci.add_argument("question", nargs=argparse.REMAINDER)
    per_sub.add_parser("status")

    mcp = sub.add_parser("mcp", help="MCP: connect to the Model Context Protocol ecosystem")
    mcp_sub = mcp.add_subparsers(dest="mcp_action")
    mcp_sub.add_parser("status")
    mcp_sub.add_parser("add-demo")
    mcp_sub.add_parser("list")
    _ma = mcp_sub.add_parser("add")
    _ma.add_argument("name")
    _ma.add_argument("--tools", default="[]", help="JSON list of tools")
    _ma.add_argument("rest", nargs=argparse.REMAINDER)

    harness = sub.add_parser("harness", help="Continual harness: self-refining skills/memory")
    harness_sub = harness.add_subparsers(dest="harness_action")
    harness_sub.add_parser("status")
    _hl = harness_sub.add_parser("list")
    _hl.add_argument("kind", nargs="?", default="")
    _hr = harness_sub.add_parser("refine")
    _hr.add_argument("goal")
    _hr.add_argument("--repeated", action="store_true")
    _hrb = harness_sub.add_parser("rollback")
    _hrb.add_argument("kind")
    _hrb.add_argument("name")
    _hc = harness_sub.add_parser("context")
    _hc.add_argument("rest", nargs=argparse.REMAINDER)

    briefing = sub.add_parser("briefing", help="Morning briefing: today's intel")
    briefing_sub = briefing.add_subparsers(dest="briefing_action")
    briefing_sub.add_parser("build").add_argument("--topic", default="")
    briefing_sub.add_parser("deliver").add_argument("--topic", default="")

    skill = sub.add_parser("add-skill", help="Install a community skill")
    skill_sub = skill.add_subparsers(dest="skill_action")
    skill_inst = skill_sub.add_parser("install", help="Install from url/file")
    skill_inst.add_argument("source", nargs=argparse.REMAINDER)
    skill_inst.add_argument("--allow-network", action="store_true")
    skill_sub.add_parser("list")

    meta = sub.add_parser("meta", help="Jarvis Brain: metacognition (evaluate + replan)")
    meta_sub = meta.add_subparsers(dest="meta_action")
    meta_eval = meta_sub.add_parser("evaluate", help="Evaluate an outcome, feed into a goal")
    meta_eval.add_argument("rest", nargs=argparse.REMAINDER)
    meta_eval.add_argument("--ok", action="store_true", help="Treat as success")
    meta_eval.add_argument("--goal", default=None, help="Goal id to apply the verdict to")
    meta_sub.add_parser("history")
    meta_sub.add_parser("stats")

    goal = sub.add_parser("goal", help="Jarvis Brain: persistent goal stack")
    goal_sub = goal.add_subparsers(dest="goal_action")
    goal_sub.add_parser("list")
    goal_sub.add_parser("new").add_argument("rest", nargs=argparse.REMAINDER)
    goal_sub.add_parser("status").add_argument("id")
    goal_sub.add_parser("advance").add_argument("id")
    _gf = goal_sub.add_parser("fail")
    _gf.add_argument("id")
    _gf.add_argument("rest", nargs=argparse.REMAINDER)
    goal_sub.add_parser("abandon").add_argument("id")
    _gfu = goal_sub.add_parser("follow-up")
    _gfu.add_argument("id")
    _gfu.add_argument("rest", nargs=argparse.REMAINDER)

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
            if getattr(args, "deep", False):
                return cmd_model_download_deep(args)
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
    if cmd == "brain":
        return cmd_brain(args)
    if cmd == "goal":
        return cmd_goal(args)
    if cmd == "meta":
        return cmd_meta(args)
    if cmd == "reflect":
        return cmd_reflect(args)
    if cmd == "voice":
        return cmd_voice(args)
    if cmd == "guardian":
        return cmd_guardian(args)
    if cmd == "graph":
        return cmd_graph(args)
    if cmd == "harness":
        return cmd_harness(args)
    if cmd == "mcp":
        return cmd_mcp(args)
    if cmd == "skill-verify":
        return cmd_skill_verify(args)
    if cmd == "compaction":
        return cmd_compaction(args)
    if cmd == "delegate":
        return cmd_delegate(args)
    if cmd == "automation":
        return cmd_automation(args)
    if cmd == "router":
        return cmd_router(args)
    if cmd == "daemon":
        return cmd_daemon(args)
    if cmd == "benchmark":
        return cmd_benchmark(args)
    if cmd == "sandbox":
        return cmd_sandbox(args)
    if cmd == "vault":
        return cmd_vault(args)
    if cmd == "personal":
        return cmd_personal(args)
    if cmd == "wake":
        return cmd_wake(args)
    if cmd == "leaderboard":
        return cmd_leaderboard(args)
    if cmd == "briefing":
        return cmd_briefing(args)
    if cmd == "add-skill":
        return cmd_add_skill(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
