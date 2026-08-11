# OMNI Away Mode — Research, Reports & RAG+CAG Memory (Phase 7)

> **Document status (2026-08-11): historical or unqualified reference.** This file records earlier intent, implementation, audit, or setup work. Its completion, test-count, performance, privacy, platform, and production-readiness statements are **not current release claims**. Use the generated [Capability Matrix](CAPABILITY_MATRIX.md) and [Quality Scorecard](QUALITY_SCORECARD.md) for current truth.


OMNI can now **take over while you're away**: queue autonomous research, monitor
and digest what happened, save everything into a local knowledge base, and
**send you reports** to your phone. Everything runs on your machine — no cloud.

It centers on a **hybrid memory** that gives you both of the things you asked for:

- **LONG-TERM memory → RAG** *(Retrieval-Augmented Generation)*
  A persistent semantic vector store over your whole knowledge base. At answer
  time OMNI *retrieves* the top-K relevant chunks and feeds them to the model.
- **SHORT / FAST memory → CAG** *(Cache-Augmented Generation)*
  A pre-computed context cache (pinned facts, ongoing tasks, recent events) that
  is *always injected* with **zero retrieval latency** — deterministic and always
  present.

**The mix:** RAG gives deep, scalable recall; CAG gives instant, always-on
short-term memory. Together that's exactly the "long term / short fast term"
split. Embeddings are computed with a **zero-dependency offline vectorizer**
(no model download, no API, no network).

---

## The command surface

```
omni kb add <file|folder|url>     # ingest knowledge locally
omni kb query "question?"         # ask the KB (RAG+CAG fused)
omni kb search <term>             # keyword search
omni kb list | stats

omni research "topic"             # run autonomous research, save report
omni away start | stop | status   # turn away-mode on/off
omni away add --kind research "topic"
omni away add --kind digest "daily"
omni away add --kind notify "call mom"
omni away list | run

omni report list                  # saved reports
omni report digest                # build a digest
```

> Install the local wheel and a declared dependency profile using the current
> workflow in [TROUBLESHOOTING.md](TROUBLESHOOTING.md), then run these as
> `omni ...`. From a checkout environment, `python -m omni.cli ...` is equivalent.

### API (FastAPI :8765)
Mounted at `/api/away` — see `backend_fastapi/away_routes.py`:
`GET /api/away/status`, `GET/POST /api/away/tasks`,
`POST /api/away/tasks/run`, `GET /api/away/kb/stats`,
`POST /api/away/kb/add`, `POST /api/away/kb/query`,
`POST /api/away/research`, `POST /api/away/reports/digest`.

---

## Getting reports to your phone

Reports are **always saved locally** under `data/reports/{date}/`. Whether a
summary also reaches your phone depends on the configured messenger
(`data/config.json`):

| Provider | How it works | Offline? |
|----------|--------------|----------|
| `file` (default) | writes to `data/messenger/outbox/` | ✅ fully offline |
| `whatsapp` | `pywhatkit` drives your local WhatsApp Web in your browser | ⚙️ local browser, needs WhatsApp Web logged in |
| `telegram` | `python-telegram-bot` sends + can **receive remote commands** | needs Telegram (a proxy in regions where it's blocked) |

For **Pakistan**, WhatsApp is the recommended channel (WhatsApp isn't blocked,
unlike Telegram). One-time setup:

```
pip install pywhatkit
omni messenger setup-whatsapp              # step-by-step guide
omni messenger whatsapp-set +923001234567  # set your number (auto +92)
omni messenger test                        # verify a test message arrives
```

Example config (`data/config.json`):
```json
{
  "messenger": {
    "provider": "whatsapp",
    "phone_number": "+923001234567"
  },
  "away": {
    "auto_start": false,
    "research_max_queries": 4,
    "report_on_complete": true
  }
}
```

If the configured provider isn't ready (e.g. `pywhatkit` missing, no phone
number, no bot token), OMNI **gracefully falls back to `file`** so the away
pipeline never crashes and the report is still saved.

---

## Remote commands from your phone

The messenger bridge also polls for **inbound** commands (Telegram bot):

```
/status                -> away + KB status
/research <topic>      -> queue autonomous research
/digest                -> build & send a digest
/kb <question>         -> ask your knowledge base
/help                  -> list commands
<anything else>        -> passed to the brain if attached
```

Incoming commands are written to `data/messenger/inbox/` for a local audit
trail. `omni_v2/away/command_channel.py` holds the pure routing logic and the
`CommandPoller` background loop.

---

## The hybrid memory internals

- `omni_v2/memory/hybrid_memory.py`
  - `remember(text, kind, source, importance, hot)` → goes to **both** RAG
    long-term corpus and CAG hot cache.
  - `pin(key, value)` → persistent, always-injected CAG context.
  - `retrieve(query, k)` → RAG semantic search (importance-weighted).
  - `build_context(question)` → **fused** CAG + RAG block for prompt injection.
- `omni_v2/away/knowledge_base.py` → chunking + file/folder/URL ingestion.
- `omni_v2/away/research.py` → autonomous multi-step research → KB + report.
- `omni_v2/away/away_agent.py` → persistent task queue + runner.
- `omni_v2/away/reporter.py` → markdown reports & digests.
- `omni_v2/away/messenger.py` → file / whatsapp / telegram bridge.
- `omni_v2/away/context.py` → `build_away_stack()` one-call wiring.

### Brain integration
`Brain` accepts a `context_provider(question)` (set via
`brain.set_context_provider(...)`). Every prompt gets the fused RAG+CAG block
injected automatically. `omni_v2/away/context.py` builds it from the KB memory.

---

## Tests

```
python -m pytest omni_v2/tests/test_hybrid_memory.py \
  omni_v2/tests/test_knowledge_base.py \
  omni_v2/tests/test_research.py \
  omni_v2/tests/test_away_agent.py \
  omni_v2/tests/test_messenger.py \
  omni_v2/tests/test_command_channel.py -q
```

These are suites 21–26 in `omni test`. They run fully offline with no model, no
network and no external providers. The desktop app + camera security have two
more suites (27–28: `test_security`, `test_desktop`) — see
[DESKTOP_SECURITY.md](DESKTOP_SECURITY.md).

## Full Python desktop app

`python omni_desktop.py` (or `omni app`) opens a customtkinter control panel for
all of this — Dashboard, Knowledge Base, Research, Away Tasks, Reports,
Messenger, and Security. It needs a display; the logic it drives
(`omni_v2/away/desktop.py`) is headless and unit-tested.
