"""
SKILL.md 파일 로더
Agent가 런타임에 SKILL.md를 읽어 동작 방침을 결정한다.
Claude Code가 CLAUDE.md/SKILL.md를 참조하는 것과 동일한 패턴.
"""
from pathlib import Path
from backend.core.config import settings


def load_skill(skill_name: str) -> str:
    """skills/{skill_name}.skill.md 내용 반환"""
    path = settings.SKILLS_DIR / f"{skill_name}.skill.md"
    if not path.exists():
        raise FileNotFoundError(f"SKILL 파일 없음: {path}")
    return path.read_text(encoding="utf-8")


def load_multiple_skills(*skill_names: str) -> dict:
    return {name: load_skill(name) for name in skill_names}


def list_available_skills() -> list:
    return [f.stem.replace(".skill", "") for f in settings.SKILLS_DIR.glob("*.skill.md")]
