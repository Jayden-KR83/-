"""
환경변수 설정 관리
API Key는 .env 파일에서만 로드 — 코드 하드코딩 절대 금지
"""
import os
from pathlib import Path

def _load_env_file():
    """
    .env 파일을 수동으로 파싱해 환경변수에 등록한다.
    python-dotenv 없이도 동작하도록 표준 라이브러리만 사용.
    """
    env_path = Path(__file__).parent.parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

_load_env_file()


class Settings:
    # Claude API
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")
    CLAUDE_MAX_TOKENS: int = int(os.getenv("CLAUDE_MAX_TOKENS", "8192"))
    CLAUDE_TEMPERATURE: float = float(os.getenv("CLAUDE_TEMPERATURE", "0.1"))

    # Server
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / os.getenv("UPLOAD_DIR", "data/uploads")
    OUTPUT_DIR: Path = BASE_DIR / os.getenv("OUTPUT_DIR", "data/outputs")
    REFERENCE_DIR: Path = BASE_DIR / os.getenv("REFERENCE_DIR", "data/reference")
    KNOWLEDGE_DIR: Path = BASE_DIR / os.getenv("KNOWLEDGE_DIR", "data/knowledge")
    SKILLS_DIR: Path = BASE_DIR / "skills"

    def validate(self) -> list[str]:
        """설정 유효성 검사. 문제 있으면 오류 목록 반환."""
        errors = []
        if not self.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY 미설정 — .env 파일에 API Key를 입력하세요")
        elif not self.ANTHROPIC_API_KEY.startswith("sk-ant-"):
            errors.append("ANTHROPIC_API_KEY 형식 오류 — sk-ant-로 시작해야 합니다")
        return errors


settings = Settings()
