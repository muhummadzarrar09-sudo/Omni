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

## The face check is now hardened (no more "basic biometrics" caveat)

OMNI uses a **pluggable verifier** in priority order:

| Backend | What it is | Accuracy |
|---------|-----------|----------|
| **LBPH** (default) | OpenCV contrib's trained `LBPHFaceRecognizer` — you enroll several images and it *learns* a model | Good; reliably rejects a clearly different person. Fully offline, no model download. |
| **Deep** | dlib `face_recognition` neural embeddings | Best-in-class; auto-activates if dlib is installed, else skips |
| **Gradient** | lightweight gradient+color descriptor | Fallback only (no extra deps) |

**Robustness fixes (the actual caveat):**
- **Multi-sample enrollment** — `omni security enroll` now captures ~6 frames
  and trains on all of them, so a single bad frame can't break enrollment.
- **Per-backend thresholds**, calibratable (`FaceAuth(threshold=...)`).
- **Persistence** — the LBPH model is saved to `data/security/owner_model.xml`
  and reloaded on the next run.

Check which backend you're on with `omni security status` (it prints `backend`).
To get the strongest accuracy, `pip install dlib face_recognition` once.

Remaining honest limit: all of these run on the face *crop* from the local Haar
detector, so very poor lighting / extreme angles still degrade results. Keep the
countdown + Cancel path, which is the safety net.

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

- `omni_v2/security/face_auth.py` — enroll + verify (LBPH / deep / gradient backends)
- `omni_v2/security/lockdown.py` — cross-platform lock + pre-lock alert/countdown
- `omni_v2/security/guard_monitor.py` — background camera watchdog
- `omni_v2/away/desktop.py` — headless `DesktopController` (unit-tested)
- `omni_desktop.py` — the customtkinter GUI
- `omni/cli.py` — `omni app` and `omni security` subcommands

## Getting reports / alerts to your phone (Pakistan)

WhatsApp is **not blocked in Pakistan** (unlike Telegram), so use WhatsApp Web:

```
pip install pywhatkit                      # once
omni messenger setup-whatsapp              # step-by-step guide
omni messenger whatsapp-set +923001234567  # set your number
omni messenger test                        # send a test message
```

Key points:
- Open `https://web.whatsapp.com` in your **default browser** and log in once
  (phone → Linked devices → scan QR). pywhatkit drives that same browser.
- The recipient must be a saved contact (and have you saved too) — WhatsApp
  needs the chat to resolve.
- Numbers are auto-normalized to `+92...` (so `03001234567` → `+923001234567`).
- If `pywhatkit` isn't installed / no number, OMNI falls back to the local
  `file` channel and still saves the report — it never silently fails.
