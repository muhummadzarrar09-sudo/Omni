#!/usr/bin/env python3
"""
OMNI DAEMON - the always-on resident agent.

Starts OMNI's background services (voice loop, proactive guardian, automation
triggers, away agent) and keeps them running. Designed to be launched at
login/boot via `omni daemon enable`.

Usage:
    omni daemon enable     # register for auto-start on boot
    omni daemon disable    # remove auto-start
    omni daemon status     # check auto-start + running services
    omni daemon start      # start resident services now
    omni daemon stop       # stop resident services
"""
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def build_resident_services():
    """Wire OMNI's resident services (guardian + automation + away) into a
    DaemonController. Voice loop is opt-in (needs real audio)."""
    from omni_v2.away.desktop import DesktopController
    from omni_v2.daemon.daemon import DaemonController
    c = DesktopController()

    services = {}
    # proactive guardian
    services["guardian"] = lambda: c.guardian_start() and (lambda: None)()
    # automation triggers (manager stays alive; fires on webhook)
    services["automation"] = lambda: c._get_triggers() and (lambda: None)()
    # away agent exists in the stack already; keep it warmed
    services["away"] = lambda: c.away.away_start() if c.away else (lambda: None)()
    return DaemonController(services=services), c


def main():
    import argparse
    from omni_v2.daemon.daemon import AutoStartManager

    p = argparse.ArgumentParser(prog="omni daemon", description="OMNI resident agent")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("enable")
    sub.add_parser("disable")
    sub.add_parser("status")
    sub.add_parser("start")
    sub.add_parser("stop")
    args = p.parse_args()
    cmd = args.cmd or "status"

    asm = AutoStartManager()

    if cmd == "enable":
        res = asm.enable()
        print(f"  ✅ Auto-start enabled ({res['backend']}): {res['command']}")
        return 0
    if cmd == "disable":
        res = asm.disable()
        print(f"  {'✅ Auto-start disabled' if res['ok'] else '❌ failed'}")
        return 0
    if cmd == "status":
        st = asm.status()
        print(f"  Auto-start: {'✅ installed' if st['installed'] else '❌ not installed'} ({st['backend']})")
        return 0
    if cmd == "start":
        daemon, _ = build_resident_services()
        res = daemon.start()
        print(f"  ▶ Resident services started: {', '.join(res['started']) or '(none)'}")
        print("  (running in background — keep this process alive)")
        # keep alive
        try:
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            daemon.stop()
        return 0
    if cmd == "stop":
        daemon, _ = build_resident_services()
        daemon.stop()
        print("  ■ Resident services stopped")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
