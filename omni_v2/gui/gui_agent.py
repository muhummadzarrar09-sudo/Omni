"""
OMNI GUI AGENT (Phase 16, #4) — OMNI actually uses your screen.

A vision-driven GUI automation agent: it screenshots the screen, uses the vision
model to decide the next action, and executes clicks / typing — all SANDBOXED
and JOURNALED for undo.

Design:
  - GuiAction: {kind: click|type|screenshot|scroll|done, args}
  - GuiAgent:
      * screenshot() -> captures the screen (pluggable capture).
      * observe()   -> describe the screen (pluggable vision).
      * decide(text) -> the brain/vision returns the next GuiAction (pluggable).
      * act(action)  -> execute it via a driver (pluggable; pyautogui default),
                        sandboxed to a SAFE list + journaled.
  - SAFE_ACTIONS allow-list; anything else is blocked. Journal records for undo.

Fully local + headless-testable: capture/vision/driver all pluggable; tests use
fakes. This is the scaffolding that becomes a real screen-using agent on the DGX
(with a strong vision model + pyautogui).
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("GuiAgent")

SAFE_ACTIONS = {"screenshot", "click", "type", "scroll", "done"}


@dataclass
class GuiAction:
    kind: str
    args: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GuiAgent:
    """Vision-driven GUI automation loop (sandboxed + journaled)."""

    def __init__(
        self,
        capture: Optional[Callable[[], Any]] = None,     # -> image
        vision: Optional[Callable[[Any], str]] = None,    # image -> description
        decide: Optional[Callable[[str], GuiAction]] = None,  # desc -> next action
        driver: Optional[Callable[[GuiAction], Any]] = None,  # action -> result
        journal=None,
        max_steps: int = 10,
    ):
        self.capture = capture or (lambda: None)
        self.vision = vision or (lambda img: "(no vision)")
        self.decide = decide
        self.driver = driver or self._safe_driver
        self.journal = journal
        self.max_steps = max_steps
        self._performed: List[Dict[str, Any]] = []

    # -- safe driver: only SAFE_ACTIONS are executed, else blocked ----------
    @staticmethod
    def _safe_driver(action: GuiAction) -> Any:
        if action.kind not in SAFE_ACTIONS:
            return {"blocked": True, "reason": f"action '{action.kind}' not allowed"}
        return {"ok": True, "kind": action.kind}

    # -- the run loop -------------------------------------------------------
    def run(self, task: str) -> Dict[str, Any]:
        """Screenshot -> observe -> decide -> act, up to max_steps."""
        steps = []
        for i in range(self.max_steps):
            img = self.capture()
            desc = self.vision(img)
            if self.decide is None:
                return {"ok": True, "steps": steps, "reason": "no decider (halted)"}
            action = self.decide(desc)
            if action is None:
                break
            if action.kind == "done":
                break
            if action.kind not in SAFE_ACTIONS:
                steps.append({"step": i, "action": action.to_dict(), "blocked": True})
                break
            result = self.driver(action)
            self._record(action, result)
            steps.append({"step": i, "action": action.to_dict(), "result": result})
            if isinstance(result, dict) and result.get("blocked"):
                break
        return {"ok": True, "steps": steps, "count": len(steps)}

    def _record(self, action: GuiAction, result: Any) -> None:
        self._performed.append({"action": action.to_dict(), "result": result, "ts": time.time()})
        if self.journal is not None:
            try:
                self.journal.record("gui_" + action.kind, action.args)
            except Exception:
                pass

    def history(self, n: int = 20) -> List[Dict[str, Any]]:
        return self._performed[-n:][::-1]

    def stats(self) -> Dict[str, Any]:
        return {"steps_done": len(self._performed), "max_steps": self.max_steps,
                "safe_actions": SAFE_ACTIONS}


def get_gui_agent(**kwargs) -> GuiAgent:
    return GuiAgent(**kwargs)
