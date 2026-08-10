#!/usr/bin/env python3
"""
OMNI DESKTOP - full Python desktop control panel (Away Mode + Security).

A single-file customtkinter GUI that wraps the whole local feature set:
  * Dashboard  - away status, KB stats, messenger, reports, security
  * Knowledge Base - add files/folders/URLs, query, list sources
  * Research   - run autonomous research -> report
  * Away Tasks - queue / run research/digest/notify tasks
  * Reports    - browse saved reports
  * Messenger  - provider config (file/whatsapp/telegram), send test message
  * Security   - enroll owner face (camera), arm/disarm guard, manual lock,
                 intruder events + lockdown history

Runs fully local. GUI needs a display + `pip install customtkinter opencv-python`.
If the GUI toolkit isn't available it prints a helpful message (the underlying
DesktopController still works headlessly via tests/CLI).

Launch:  python omni_desktop.py        (or)   omni app
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _launch_gui():
    try:
        import customtkinter as ctk  # noqa: PLC0415
    except Exception as e:
        print("OMNI Desktop needs a GUI + customtkinter. Install and run on your machine:")
        print("    pip install customtkinter opencv-python")
        print(f"    python omni_desktop.py\n(GUI unavailable here: {e})")
        return 1

    import threading
    from omni_v2.away.desktop import DesktopController

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("OMNI — Away & Security")
    app.geometry("1100x720")
    controller = DesktopController()

    # ---------- helper: run blocking work on a thread, then callback ----------
    def bg(fn, on_done):
        def runner():
            try:
                res = fn()
            except Exception as e:
                res = {"ok": False, "detail": str(e)}
            if on_done:
                app.after(0, lambda: on_done(res))
        threading.Thread(target=runner, daemon=True).start()

    def log_box(box, text):
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", text)
        box.configure(state="disabled")

    tabs = ctk.CTkTabview(app)
    tabs.pack(fill="both", expand=True, padx=12, pady=12)

    # ================= DASHBOARD =================
    t_dash = tabs.add("Dashboard")
    dash = ctk.CTkTextbox(t_dash, height=540, font=("Consolas", 13))
    dash.pack(fill="both", expand=True, padx=8, pady=8)
    def refresh_dash():
        def done(st):
            import json
            log_box(dash, json.dumps(st, indent=2, default=str))
        bg(lambda: controller.status(), done)
    ctk.CTkButton(t_dash, text="Refresh", command=refresh_dash).pack(pady=6)
    refresh_dash()

    # ================= KNOWLEDGE BASE =================
    t_kb = tabs.add("Knowledge Base")
    ctk.CTkLabel(t_kb, text="Add file / folder / URL:").pack(anchor="w", padx=8)
    kb_target = ctk.CTkEntry(t_kb, placeholder_text="C:/docs/manual.md  or  https://example.com/page")
    kb_target.pack(fill="x", padx=8)
    kb_add_btn = ctk.CTkButton(t_kb, text="Add to KB", width=120)
    kb_add_btn.pack(anchor="w", padx=8, pady=4)
    ctk.CTkLabel(t_kb, text="Ask the KB:").pack(anchor="w", padx=8)
    kb_q = ctk.CTkEntry(t_kb, placeholder_text="how do I deploy the api?")
    kb_q.pack(fill="x", padx=8)
    kb_q_btn = ctk.CTkButton(t_kb, text="Query", width=120)
    kb_q_btn.pack(anchor="w", padx=8, pady=4)
    kb_out = ctk.CTkTextbox(t_kb, height=300, font=("Consolas", 12))
    kb_out.pack(fill="both", expand=True, padx=8, pady=8)

    def do_kb_add():
        t = kb_target.get().strip()
        if not t:
            return
        def done(res):
            kb_target.delete(0, "end")
            log_box(kb_out, ("✅ " + res.get("detail", "") + f"\n({res.get('chunks',0)} chunks)") if res.get("ok") else ("❌ " + res.get("detail", "")))
        bg(lambda: controller.kb_add(t), done)
    def do_kb_query():
        q = kb_q.get().strip()
        if not q:
            return
        def done(res):
            kb_q.delete(0, "end")
            if res.get("ok") is False:
                log_box(kb_out, "❌ " + res.get("detail", ""))
                return
            log_box(kb_out, res.get("context", "no context"))
        bg(lambda: controller.kb_query(q), done)
    kb_add_btn.configure(command=do_kb_add)
    kb_q_btn.configure(command=do_kb_query)

    # ================= RESEARCH =================
    t_rs = tabs.add("Research")
    ctk.CTkLabel(t_rs, text="Research topic:").pack(anchor="w", padx=8)
    rs_topic = ctk.CTkEntry(t_rs, placeholder_text="quantum computing for beginners")
    rs_topic.pack(fill="x", padx=8)
    rs_btn = ctk.CTkButton(t_rs, text="Run Research", width=140)
    rs_btn.pack(anchor="w", padx=8, pady=4)
    rs_out = ctk.CTkTextbox(t_rs, height=420, font=("Consolas", 12))
    rs_out.pack(fill="both", expand=True, padx=8, pady=8)
    def do_research():
        topic = rs_topic.get().strip()
        if not topic:
            return
        rs_btn.configure(state="disabled", text="Researching…")
        def done(res):
            rs_btn.configure(state="normal", text="Run Research")
            rs_topic.delete(0, "end")
            if res.get("ok"):
                log_box(rs_out, res["markdown"] + f"\n\n📄 Saved: {res['path']}")
            else:
                log_box(rs_out, "❌ " + res.get("detail", ""))
        bg(lambda: controller.run_research(topic), done)
    rs_btn.configure(command=do_research)

    # ================= AWAY TASKS =================
    t_away = tabs.add("Away Tasks")
    top = ctk.CTkFrame(t_away)
    top.pack(fill="x", padx=8, pady=4)
    kind_var = ctk.StringVar(value="research")
    ctk.CTkOptionMenu(top, values=["research", "digest", "notify"], variable=kind_var, width=110).pack(side="left", padx=4)
    away_brief = ctk.CTkEntry(top, placeholder_text="task brief / topic / message")
    away_brief.pack(side="left", fill="x", expand=True, padx=4)
    away_add = ctk.CTkButton(top, text="Queue", width=80)
    away_add.pack(side="left", padx=4)
    away_run = ctk.CTkButton(t_away, text="Run pending now", width=140)
    away_run.pack(anchor="w", padx=8, pady=4)
    away_toggle = ctk.CTkButton(t_away, text="Toggle Away mode", width=160)
    away_toggle.pack(anchor="w", padx=8)
    away_list = ctk.CTkTextbox(t_away, height=360, font=("Consolas", 12))
    away_list.pack(fill="both", expand=True, padx=8, pady=8)

    def refresh_away():
        bg(lambda: controller.away_list(),
           lambda lst: log_box(away_list, "".join(
               f"[{t['status']}] {t['kind']}: {t['brief']}\n" for t in lst) or "queue empty"))
    def do_away_add():
        brief = away_brief.get().strip()
        if not brief:
            return
        kind = kind_var.get()
        def done(res):
            away_brief.delete(0, "end")
            refresh_away()
        bg(lambda: controller.away_submit(kind, brief), done)
    def do_away_run():
        def done(res):
            refresh_away()
        bg(lambda: {"ran": controller.away_run_pending()}, done)
    away_add.configure(command=do_away_add)
    away_run.configure(command=do_away_run)
    away_toggle.configure(command=lambda: bg(
        lambda: controller.away_start_stop(not (controller.away.active if controller.away else False)), lambda r: refresh_away()))
    refresh_away()

    # ================= REPORTS =================
    t_rep = tabs.add("Reports")
    rep_btn = ctk.CTkButton(t_rep, text="Refresh reports", width=140)
    rep_btn.pack(anchor="w", padx=8, pady=4)
    rep_out = ctk.CTkTextbox(t_rep, height=520, font=("Consolas", 12))
    rep_out.pack(fill="both", expand=True, padx=8, pady=8)
    def refresh_reports():
        def done(r):
            import json
            log_box(rep_out, json.dumps(r, indent=2, default=str))
        bg(lambda: controller.reporter.list_recent(20), done)
    rep_btn.configure(command=refresh_reports)
    refresh_reports()

    # ================= MESSENGER =================
    t_msg = tabs.add("Messenger")
    cfg = controller.messenger_config()
    msg_cfg = cfg.get("messenger", {})
    mf = ctk.CTkFrame(t_msg)
    mf.pack(fill="x", padx=8, pady=4)
    ctk.CTkLabel(mf, text="Provider:").grid(row=0, column=0, sticky="w", padx=4)
    prov_var = ctk.StringVar(value=msg_cfg.get("provider", "file"))
    ctk.CTkOptionMenu(mf, values=["file", "whatsapp", "telegram"], variable=prov_var, width=120).grid(row=0, column=1, sticky="w")
    ctk.CTkLabel(mf, text="Phone (wa):").grid(row=1, column=0, sticky="w", padx=4)
    phone_e = ctk.CTkEntry(mf, placeholder_text="+92300...")
    phone_e.grid(row=1, column=1, padx=4, pady=2)
    ctk.CTkLabel(mf, text="TG token:").grid(row=2, column=0, sticky="w", padx=4)
    tok_e = ctk.CTkEntry(mf, placeholder_text="bot token")
    tok_e.grid(row=2, column=1, padx=4, pady=2)
    ctk.CTkLabel(mf, text="TG chat id:").grid(row=3, column=0, sticky="w", padx=4)
    chat_e = ctk.CTkEntry(mf, placeholder_text="chat id")
    chat_e.grid(row=3, column=1, padx=4, pady=2)
    phone_e.insert(0, msg_cfg.get("phone_number", ""))
    tok_e.insert(0, msg_cfg.get("token", ""))
    chat_e.insert(0, str(msg_cfg.get("chat_id", "")))
    msg_save = ctk.CTkButton(t_msg, text="Save config", width=140)
    msg_save.pack(anchor="w", padx=8, pady=4)
    msg_test = ctk.CTkButton(t_msg, text="Send test message", width=160)
    msg_test.pack(anchor="w", padx=8)
    msg_out = ctk.CTkTextbox(t_msg, height=380, font=("Consolas", 12))
    msg_out.pack(fill="both", expand=True, padx=8, pady=8)
    def do_save_cfg():
        cfg["messenger"] = {
            "provider": prov_var.get(),
            "phone_number": phone_e.get().strip(),
            "token": tok_e.get().strip(),
            "chat_id": chat_e.get().strip(),
        }
        def done(_):
            log_box(msg_out, "Config saved. Restart to apply provider.")
        bg(lambda: controller.save_config(cfg), done)
    def do_test():
        def done(res):
            log_box(msg_out, f"{'✅' if res['ok'] else '❌'} {res.get('detail','')} (channel: {res.get('channel')})")
        bg(lambda: controller.send_message("🧪 Test from OMNI Desktop"), done)
    msg_save.configure(command=do_save_cfg)
    msg_test.configure(command=do_test)

    # ================= IDENTITY (Jarvis Brain B1/B7) =================
    t_id = tabs.add("Identity")
    id_btn = ctk.CTkButton(t_id, text="Show Identity", width=140)
    id_btn.pack(anchor="w", padx=8, pady=4)
    id_out = ctk.CTkTextbox(t_id, height=400, font=("Consolas", 12))
    id_out.pack(fill="both", expand=True, padx=8, pady=8)
    id_row = ctk.CTkFrame(t_id)
    id_row.pack(fill="x", padx=8)
    id_name = ctk.CTkEntry(id_row, placeholder_text="your name")
    id_name.pack(side="left", fill="x", expand=True, padx=4)
    id_save = ctk.CTkButton(id_row, text="Set user name", width=120)
    id_save.pack(side="left", padx=4)
    def refresh_identity():
        def done(st):
            import json
            log_box(id_out, json.dumps(st, indent=2, default=str))
        bg(lambda: controller.identity.stats() if getattr(controller, "identity", None) else {}, done)
    def do_id_save():
        n = id_name.get().strip()
        if n:
            def done(res):
                id_name.delete(0, "end")
                refresh_identity()
            bg(lambda: controller.identity.update_user(name=n), done)
    id_btn.configure(command=refresh_identity)
    id_save.configure(command=do_id_save)
    refresh_identity()

    # ================= GOALS (Jarvis Brain) =================
    t_goal = tabs.add("Goals")
    g_row = ctk.CTkFrame(t_goal)
    g_row.pack(fill="x", padx=8, pady=4)
    g_intent = ctk.CTkEntry(g_row, placeholder_text="e.g. build a habit tracker")
    g_intent.pack(side="left", fill="x", expand=True, padx=4)
    g_new = ctk.CTkButton(g_row, text="New goal", width=100)
    g_new.pack(side="left", padx=4)
    g_adv = ctk.CTkButton(g_row, text="Advance", width=90)
    g_adv.pack(side="left", padx=4)
    g_out = ctk.CTkTextbox(t_goal, height=420, font=("Consolas", 12))
    g_out.pack(fill="both", expand=True, padx=8, pady=8)
    def refresh_goals():
        def done(lst):
            if not lst:
                log_box(g_out, "(no goals — type one above and click New goal)")
                return
            lines = []
            for g in lst:
                mark = {"pending": "○", "active": "▶", "done": "✔", "blocked": "✘", "abandoned": "⊘"}.get(g["status"], "?")
                lines.append(f"{mark} {g['title']}  [{g['status']}]  {g['progress']:.0%}")
                for s in g["steps"]:
                    sm = {"pending": "  ·", "running": "  ▶", "done": "  ✔", "failed": "  ✘"}.get(s["status"], "  ·")
                    lines.append(f"     {sm} {s['desc']}")
                    if s.get("error"):
                        lines.append(f"        ERROR: {s['error']}")
                lines.append("")
            log_box(g_out, "\n".join(lines))
        bg(lambda: controller.goal_list(), done)
    def do_goal_new():
        i = g_intent.get().strip()
        if not i:
            return
        def done(res):
            g_intent.delete(0, "end")
            refresh_goals()
        bg(lambda: controller.goal_create(i), done)
    def do_goal_adv():
        def done(res):
            refresh_goals()
        # advance the first active goal for simplicity
        gs = controller.goal_list()
        if gs:
            gid = next((g["id"] for g in gs if g["status"] in ("active", "pending")), gs[0]["id"])
            bg(lambda: controller.goal_begin(gid) and controller.goal_complete_step(gid, {"ok": True}), done)
    g_new.configure(command=do_goal_new)
    g_adv.configure(command=do_goal_adv)
    refresh_goals()

    # ================= PATTERNS (Jarvis Brain) =================
    t_pat = tabs.add("Patterns")
    p_btn = ctk.CTkButton(t_pat, text="Detect patterns", width=150)
    p_btn.pack(anchor="w", padx=8, pady=4)
    p_out = ctk.CTkTextbox(t_pat, height=420, font=("Consolas", 12))
    p_out.pack(fill="both", expand=True, padx=8, pady=8)
    def refresh_patterns():
        def done(res):
            pats = res.get("patterns", []) if isinstance(res, dict) else []
            if not pats:
                log_box(p_out, "(no notable patterns)")
                return
            lines = []
            for p in pats:
                sev = {"0": "⚪", "1": "🟡", "2": "🔴"}.get(str(p["severity"]), "·")
                lines.append(f"{sev} {p['title']}\n   {p['body']}\n")
            log_box(p_out, "\n".join(lines))
        bg(lambda: controller.detect_patterns(days=7), done)
    p_btn.configure(command=refresh_patterns)
    refresh_patterns()

    # ================= EPISODES (Jarvis Brain) =================
    t_ep = tabs.add("Episodes")
    e_row = ctk.CTkFrame(t_ep)
    e_row.pack(fill="x", padx=8, pady=4)
    e_recap = ctk.CTkButton(e_row, text="Reflect today", width=120)
    e_recap.pack(side="left", padx=4)
    e_out = ctk.CTkTextbox(t_ep, height=420, font=("Consolas", 12))
    e_out.pack(fill="both", expand=True, padx=8, pady=8)
    def refresh_episodes():
        def done(eps):
            if not eps:
                log_box(e_out, "(no episodes yet — click Reflect today)")
                return
            lines = [f"[{e['day']}] {e['summary']}" for e in eps]
            log_box(e_out, "\n".join(lines))
        bg(lambda: controller.reflector_episodes(), done)
    def do_reflect_today():
        def done(res):
            refresh_episodes()
        bg(lambda: controller.reflect_today(), done)
    e_recap.configure(command=do_reflect_today)
    refresh_episodes()

    # ================= SECURITY =================
    t_sec = tabs.add("Security")
    srow = ctk.CTkFrame(t_sec)
    srow.pack(fill="x", padx=8, pady=4)
    sec_enroll = ctk.CTkButton(srow, text="📸 Enroll Owner (camera)", width=180)
    sec_enroll.pack(side="left", padx=4)
    sec_arm = ctk.CTkButton(srow, text="Arm Guard", width=120)
    sec_arm.pack(side="left", padx=4)
    sec_disarm = ctk.CTkButton(srow, text="Disarm", width=100)
    sec_disarm.pack(side="left", padx=4)
    sec_cancel = ctk.CTkButton(srow, text="Cancel lockdown", width=140)
    sec_cancel.pack(side="left", padx=4)
    sec_lock = ctk.CTkButton(srow, text="🔒 Lock now", width=110)
    sec_lock.pack(side="left", padx=4)
    sec_out = ctk.CTkTextbox(t_sec, height=430, font=("Consolas", 12))
    sec_out.pack(fill="both", expand=True, padx=8, pady=8)

    controller.set_intruder_hook(lambda ev: app.after(
        0, lambda: log_box(sec_out, "🚨 INTRUDER DETECTED — alerting + locking shortly.\n" + str(ev))))

    def do_enroll():
        def done(res):
            log_box(sec_out, ("✅ " + res["detail"]) if res["ok"] else ("❌ " + res["detail"]))
        bg(lambda: controller.enroll_owner(), done)
    def do_arm():
        def done(res):
            log_box(sec_out, res["detail"])
        bg(lambda: controller.guard_arm(), done)
    def do_disarm():
        def done(_):
            log_box(sec_out, "Guard disarmed.")
        bg(controller.guard_disarm, done)
    def do_lock():
        def done(res):
            log_box(sec_out, res.get("detail", "locking"))
        bg(lambda: controller.manual_lock(), done)
    def do_cancel():
        controller.cancel_lockdown()
        log_box(sec_out, "Cancelled pending lockdown (if any).")
    sec_enroll.configure(command=do_enroll)
    sec_arm.configure(command=do_arm)
    sec_disarm.configure(command=do_disarm)
    sec_lock.configure(command=do_lock)
    sec_cancel.configure(command=do_cancel)

    # initial security status
    def refresh_sec():
        def done(res):
            from omni_v2.away.desktop import DesktopController
            labels = {"lbph": "OpenCV LBPH (trained, local)", "deep": "dlib deep embeddings",
                      "gradient": "gradient fallback"}
            log_box(sec_out, (
                f"Backend : {labels.get(res.get('backend','?'), res.get('backend','?'))}\n"
                f"Enrolled : {'✅ yes' if res.get('enrolled') else '❌ no'}\n"
                f"Threshold: {res.get('threshold')}   Samples: {res.get('samples')}\n"
                f"Owner file: {res.get('owner_path')}\n"))
        bg(lambda: controller.face_auth.stats() if controller.face_auth else {}, done)
    refresh_sec()

    app.mainloop()
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-v"):
        print("OMNI Desktop v3.2.0")
        return 0
    return _launch_gui()


if __name__ == "__main__":
    sys.exit(main())
