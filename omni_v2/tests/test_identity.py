"""
Tests for the Jarvis Identity Core (B1) + User Model (B7).
Run: python -m pytest omni_v2/tests/test_identity.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_id_")))

from omni_v2.brain.identity import IdentityCore, UserModel, get_identity


def test_default_identity():
    with tempfile.TemporaryDirectory() as tmp:
        ic = IdentityCore(identity_path=Path(tmp) / "identity.json")
        assert ic.name == "OMNI"
        assert "privacy" in ic.values
        assert ic.mood == "neutral"


def test_set_name_persists():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "identity.json"
        ic = IdentityCore(identity_path=p)
        ic.set_name("Jarvis")
        ic2 = IdentityCore(identity_path=p)
        assert ic2.name == "Jarvis"


def test_update_user():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "identity.json"
        ic = IdentityCore(identity_path=p)
        ic.update_user(name="Zarrar", style="professional", likes=["python", "privacy"])
        assert ic.user.name == "Zarrar"
        assert ic.user.style == "professional"
        assert "python" in ic.user.likes
        # persists
        ic2 = IdentityCore(identity_path=p)
        assert ic2.user.name == "Zarrar"


def test_add_reflection():
    with tempfile.TemporaryDirectory() as tmp:
        ic = IdentityCore(identity_path=Path(tmp) / "identity.json")
        ic.add_reflection("user is stuck on the auth refactor", kind="pattern")
        assert len(ic.reflections) == 1
        assert ic.reflections[0]["kind"] == "pattern"


def test_set_goals_today():
    with tempfile.TemporaryDirectory() as tmp:
        ic = IdentityCore(identity_path=Path(tmp) / "identity.json")
        ic.set_goals_today(["ship the habit tracker", "clear inbox"])
        assert ic.goals_today == ["ship the habit tracker", "clear inbox"]


def test_prompt_block_contains_identity_and_user():
    with tempfile.TemporaryDirectory() as tmp:
        ic = IdentityCore(identity_path=Path(tmp) / "identity.json")
        ic.set_name("OMNI")
        ic.update_user(name="Zarrar")
        block = ic.to_prompt_block()
        assert "OMNI IDENTITY" in block
        assert "Name: OMNI" in block
        assert "THE USER" in block
        assert "Zarrar" in block


def test_mood_syncs_to_personality():
    # Fake personality engine with set_mood
    class FakePersonality:
        def __init__(self):
            self.mood = None
        def set_mood(self, m):
            self.mood = m
    with tempfile.TemporaryDirectory() as tmp:
        fp = FakePersonality()
        ic = IdentityCore(identity_path=Path(tmp) / "identity.json", personality_engine=fp)
        ic.set_mood("playful")
        assert ic.mood == "playful"
        assert fp.mood == "playful"


def test_stats():
    with tempfile.TemporaryDirectory() as tmp:
        ic = IdentityCore(identity_path=Path(tmp) / "identity.json")
        ic.update_user(name="Zarrar")
        st = ic.stats()
        assert st["name"] == "OMNI"
        assert st["user"]["name"] == "Zarrar"


def test_brain_identity_injection():
    """The Brain should inject the identity block into the system prompt."""
    with tempfile.TemporaryDirectory() as tmp:
        ic = IdentityCore(identity_path=Path(tmp) / "identity.json")
        ic.set_name("OMNI")
        ic.update_user(name="Zarrar")
        from omni_v2.llm.brain import Brain
        # construct brain in regex-only mode (no model) with identity
        b = Brain(plugin_manager=None, identity=ic)
        assert b.identity is not None
        block = b.identity.to_prompt_block()
        assert "OMNI" in block


def test_get_identity_singleton():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["OMNI_DATA_DIR"] = tmp
        a = get_identity()
        b = get_identity()
        assert a is b


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
