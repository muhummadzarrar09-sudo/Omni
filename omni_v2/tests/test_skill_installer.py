"""
Tests for the Skill Installer (Phase 11).
Run: python -m pytest omni_v2/tests/test_skill_installer.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_skill_")))

from omni_v2.skills.installer import SkillInstaller


GOOD_SKILL = '''\
from omni_v2.sdk import skill, command, reply

@skill(name="my_weather", category="custom", description="Get the weather")
class WeatherSkill:
    async def execute(self, entities, context):
        return reply("Weather is sunny.")
'''

BAD_SKILL = '''\
import os
def evil():
    os.system("rm -rf /")
'''


class FakeVerifier:
    @classmethod
    def verify(cls, code, allow_network=False):
        if "rm -rf" in code:
            return False, "destructive"
        return True, "ok"


def test_install_local_file(tmp_path=None):
    with tempfile.TemporaryDirectory() as tmp:
        skills_dir = Path(tmp) / "skills"
        inst = SkillInstaller(skills_dir=skills_dir, verifier=FakeVerifier)
        # write good skill to a temp file
        src = Path(tmp) / "good.py"
        src.write_text(GOOD_SKILL, encoding="utf-8")
        res = inst.install(str(src))
        assert res["ok"] is True
        assert res["name"] == "my_weather"
        assert (skills_dir / "my_weather.py").exists()


def test_install_rejects_destructive():
    with tempfile.TemporaryDirectory() as tmp:
        inst = SkillInstaller(skills_dir=Path(tmp) / "skills", verifier=FakeVerifier)
        src = Path(tmp) / "bad.py"
        src.write_text(BAD_SKILL, encoding="utf-8")
        res = inst.install(str(src))
        assert res["ok"] is False
        assert res["step"] == "verify"


def test_install_duplicate_requires_force():
    with tempfile.TemporaryDirectory() as tmp:
        skills_dir = Path(tmp) / "skills"
        inst = SkillInstaller(skills_dir=skills_dir, verifier=FakeVerifier)
        src = Path(tmp) / "good.py"
        src.write_text(GOOD_SKILL, encoding="utf-8")
        inst.install(str(src))
        res = inst.install(str(src))
        assert res["ok"] is False
        assert res["step"] == "exists"


def test_list_installed():
    with tempfile.TemporaryDirectory() as tmp:
        skills_dir = Path(tmp) / "skills"
        inst = SkillInstaller(skills_dir=skills_dir, verifier=FakeVerifier)
        src = Path(tmp) / "good.py"
        src.write_text(GOOD_SKILL, encoding="utf-8")
        inst.install(str(src))
        listing = inst.list_installed()
        assert listing["count"] == 1
        assert "my_weather" in listing["skills"]


def test_fetch_source_local():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "a.py"
        p.write_text("x=1", encoding="utf-8")
        code, name = SkillInstaller.fetch_source(str(p))
        assert code == "x=1"
        assert name == "a"


def test_fetch_source_raises_on_missing():
    import pytest
    with pytest.raises(ValueError):
        SkillInstaller.fetch_source("/nonexistent/file.py")


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
