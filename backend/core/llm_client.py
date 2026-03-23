"""
Claude API 클라이언트
--------------------------------------------------
⚠️  보안 주의사항:
  - API Key는 .env 파일에서만 로드 (코드 하드코딩 금지)
  - CDP 데이터 전송 전 민감정보 포함 여부 확인 필요
  - API 호출 로그에 전체 응답 내용 출력 금지
--------------------------------------------------
"""
import json
import urllib.request
import urllib.error
import logging
from typing import Optional

from backend.core.config import settings

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class ClaudeClient:
    """
    Anthropic Claude API 클라이언트.
    표준 라이브러리(urllib)만 사용 — anthropic SDK 없이도 동작.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.CLAUDE_MODEL

        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY가 설정되지 않았습니다.\n"
                ".env 파일에 ANTHROPIC_API_KEY=sk-ant-... 를 추가하세요."
            )

    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Claude API /v1/messages 호출.

        Args:
            prompt: 사용자 입력
            system_prompt: 시스템 지시문 (SKILL.md 내용 등)
            temperature: 낮을수록 일관된 출력 (채점에는 0.1 권장)
            max_tokens: 최대 출력 토큰
        """
        payload = {
            "model": self.model,
            "max_tokens": max_tokens or settings.CLAUDE_MAX_TOKENS,
            "temperature": temperature if temperature is not None else settings.CLAUDE_TEMPERATURE,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        }

        req = urllib.request.Request(
            ANTHROPIC_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                # 응답에서 텍스트 추출
                for block in result.get("content", []):
                    if block.get("type") == "text":
                        return block["text"]
                return ""

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code == 401:
                raise ValueError(f"API Key 인증 실패. .env 파일의 키를 확인하세요. ({body[:200]})")
            elif e.code == 429:
                raise RuntimeError(f"API 호출 한도 초과 (Rate limit). 잠시 후 재시도하세요.")
            else:
                raise RuntimeError(f"Claude API 오류 {e.code}: {body[:500]}")

        except urllib.error.URLError as e:
            raise ConnectionError(f"네트워크 연결 실패: {e.reason}")

    def is_available(self) -> bool:
        """API Key와 네트워크 연결 상태 확인"""
        try:
            # 최소 토큰으로 연결 테스트
            self.chat("ping", max_tokens=5)
            return True
        except Exception:
            return False


# 싱글턴
_client: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    global _client
    if _client is None:
        _client = ClaudeClient()
    return _client
