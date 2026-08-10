# OMNI Desktop App & Camera Security (Phase 8)

A full **Python desktop control panel** for Away Mode + Security. No Node.js
needed — this is a single Python app (`customtkinter`).

```
pip install customtkinter opencv-python      # once, on your machine
python omni_desktop.py                       # or: omni app
```

> The GUI needs a display. In headless/CI it prints a friendly message; the
> underlying logic (`omni_v2.away.desktop.DesktopController`) is headless and
> unit-tested.

## Tabs

| Tab | What it does |
|-----|--------------|
| **Dashboard** | away-mode status, KB stats, messenger channel, recent reports, security state |
| **Knowledge Base** | add files/folders/URLs, ask the hybrid RAG+CAG KB |
| **Research** | run autonomous research → live report + saved markdown |
| **Away Tasks** | queue research/digest/notify, run pending, toggle away mode |
| **Reports** | browse saved reports |
| **Messenger** | configure provider (file/whatsapp/telegram), send a test message |
| **Security** | enroll owner, arm/disarm guard, cancel lockdown, lock now, event history |

## Camera security ("is it me?")

Fully local, no cloud. OpenCV face detection + a lightweight identity
descriptor you enroll once.

1. **Enroll your face** — `omni security enroll` (or the Security tab):
   looks at the camera, stores a descriptor in `data/security/owner.json`.
2. **Arm the guard** — `omni security arm` (or the app):
   a background watchdog samples the camera every ~2s and verifies the person.
3. **On an unrecognized face** (N consecutive frames to avoid false positives):
   1. fires a **pre-lock alert** via your messenger (WhatsApp/Telegram) —
      *"⚠️ OMNI security: suspicious activity. Locking in 10s."*
   2. runs a **countdown** (cancel from the app if it's really you)
   3. **locks the machine** (`LockWorkStation` on Windows, `loginctl`/`dm-tool`
      on Linux, `pmset` on macOS).

```
omni security status     # enrolled? threshold?
omni security enroll     # capture owner face
omni security arm        # start watchdog
omni security disarm     # stop watchdog
omni security snapshot   # one-shot verdict now
omni security lock       # manual lockdown
```

## Honest limits of the face check

This is a **basic local biometric check**, not military-grade (no neural
face-embedding model). It reliably catches *someone clearly different* at the
machine in good lighting, but it is affected by angle, light and occlusion.
For high-stakes use, swap the embedding in `FaceAuth` (the `verify()` interface
is designed for that) — e.g. a trained face-recognition model. Always keep a
way to cancel during the countdown.

## Design for safety

- The guard **requires enrollment** before it can arm (no accidental lockouts
  from a never-configured owner).
- It requires **N consecutive unknown verdicts** (default 3) so a quick glance
  away doesn't lock your machine.
- **No face** ≠ intruder — absence alone never triggers a lock.
- The alert fires **before** the lock, and the app gives you a **Cancel**
  button during the countdown.
- All events are recorded to `data/security/lockdown.json` for an audit trail.

## Files

- `omni_v2/security/face_auth.py` — enroll + verify (OpenCV, local)
- `omni_v2/security/lockdown.py` — cross-platform lock + pre-lock alert/countdown
- `omni_v2/security/guard_monitor.py` — background camera watchdog
- `omni_v2/away/desktop.py` — headless `DesktopController` (unit-tested)
- `omni_desktop.py` — the customtkinter GUI
- `omni/cli.py` — `omni app` and `omni security` subcommands
