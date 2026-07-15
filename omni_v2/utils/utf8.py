"""
Windows console UTF-8 fix.

Python on Windows defaults to cp1252 for stdout/stderr, which can't print
emoji (✅, 🔊, →, etc.) or other non-ASCII characters. This is the #1 cause
of "UnicodeEncodeError: 'charmap' codec can't encode character" on Windows.

Call `setup_utf8_console()` at the top of any entry point that might print
emoji. Idempotent — safe to call multiple times.
"""
import sys
import os


def setup_utf8_console() -> bool:
    """
    Force stdout and stderr to UTF-8 on Windows. Returns True if anything was
    changed (useful for tests).
    """
    changed = False
    # Method 1: PYTHONIOENCODING env var (works for child processes too)
    if sys.platform == "win32" and os.environ.get("PYTHONIOENCODING") != "utf-8":
        os.environ["PYTHONIOENCODING"] = "utf-8"
        changed = True
    # Method 2: reconfigure stdout/stderr if they're TextIOWrapper
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        # Try to reconfigure (Python 3.7+)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                current_encoding = getattr(stream, "encoding", None)
                if current_encoding and current_encoding.lower().replace("-", "") != "utf8":
                    reconfigure(encoding="utf-8", errors="replace")
                    changed = True
            except Exception:
                pass
    return changed
