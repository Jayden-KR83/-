"""
자동 채점 Agent (Phase 2)
skills/scoring_criteria.skill.md 지침을 따름.
Claude API로 4개 카테고리 기반 채점 + 감점 리포트 생성.
"""
import json
import time
import logging
from typing import Optional

from backend.core.models import (
    AgentResult, AgentStatus, ValidationResult,
    ScoringResult, DeductionItem,
)
from backend.core.skill_loader import load_skill
from backend.core.llm_client import get_claude_client

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


def _build_scoring_prompt(
    question_id: str,
    question_text: str,
    answer_text: str,
    max_points: float,
    reference_data: Optional[str] = None,
) -> str:
    ref_section = f"\n\n[참고 데이터]\n{reference_data}" if reference_data else ""
    return f"""다음 CDP 답변을 채점해주세요.

[문항 ID] {question_id}
[문항 내용] {question_text}
[최고 배점] {max_points}점
[제출 답변]
{answer_text}{ref_section}

아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{{
  "score": <0~{max_points} 실수>,
  "deductions": [
    {{"category": "완전성|정확성|일관성|구체성", "reason": "구체적 감점 이유", "points_deducted": <실수>}}
  ],
  "improvements": ["개선 제안 1", "개선 제안 2"],
  "confidence": "높음|보통|낮음"
}}

채점 기준:
- 완전성(Completeness): 필수 정보가 모두 포함되었는가
- 정확성(Accuracy): 수치, 단위, 기준연도가 정확한가
- 일관성(Consistency): 다른 문항과의 데이터 일치 여부
- 구체성(Specificity): 일반론이 아닌 회사 특정 내용인가
"""


def _parse_scoring_response(raw: str, max_points: float) -> Optional[ScoringResult]:
    """Claude 응답에서 JSON 파싱"""
    try:
        # JSON 블록 추출
        text = raw.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            return None
        data = json.loads(text[start:end])

        score = float(data.get("score", 0))
        score = max(0.0, min(score, max_points))  # 범위 클램프

        deductions = [
            DeductionItem(
                category=d.get("category", "기타"),
                reason=d.get("reason", ""),
                points_deducted=float(d.get("points_deducted", 0)),
            )
            for d in data.get("deductions", [])
        ]

        improvements = [str(i) for i in data.get("improvements", [])]
        confidence = data.get("confidence", "보통")

        return ScoringResult(
            question_id="",  # caller가 설정
            score=score,
            max_score=max_points,
            percentage=round(score / max_points * 100, 1) if max_points > 0 else 0.0,
            deductions=deductions,
            improvements=improvements,
            confidence=confidence,
        )
    except Exception as e:
        logger.warning(f"채점 응답 파싱 실패: {e}\n원문: {raw[:300]}")
        return None


def run_scoring_agent(
    question_id: str,
    question_text: str,
    answer_text: str,
    max_points: float,
    reference_data: Optional[str] = None,
) -> AgentResult:
    """
    CDP 답변 자동 채점.

    Args:
        question_id: 문항 ID (예: C1.1)
        question_text: 문항 내용
        answer_text: 제출된 답변 텍스트
        max_points: 최고 배점
        reference_data: 선택적 참고 데이터 (이전 답변, 기준 데이터 등)

    Returns:
        AgentResult (data: ScoringResult)
    """
    t_start = time.time()
    skill_text = load_skill("scoring_criteria")
    client = get_claude_client()

    prompt = _build_scoring_prompt(
        question_id, question_text, answer_text, max_points, reference_data
    )

    scoring_result: Optional[ScoringResult] = None
    last_error = ""
    retry_count = 0

    for attempt in range(MAX_RETRIES + 1):
        try:
            raw = client.chat(
                prompt=prompt,
                system_prompt=skill_text,
                temperature=0.1,
            )
            scoring_result = _parse_scoring_response(raw, max_points)
            if scoring_result:
                scoring_result.question_id = question_id
                break
            last_error = "JSON 파싱 실패"
        except Exception as e:
            last_error = str(e)
            logger.warning(f"채점 시도 {attempt + 1} 실패: {e}")

        retry_count = attempt + 1
        if attempt < MAX_RETRIES:
            time.sleep(1)

    elapsed = round(time.time() - t_start, 2)

    if not scoring_result:
        return AgentResult(
            agent_name="scoring_agent",
            status=AgentStatus.FAILED,
            error_message=f"채점 실패 ({MAX_RETRIES + 1}회 시도): {last_error}",
            processing_time_sec=elapsed,
            retry_count=retry_count,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

    # 신뢰도 매핑
    conf_map = {"높음": 0.9, "보통": 0.7, "낮음": 0.45}
    conf_score = conf_map.get(scoring_result.confidence, 0.7)
    needs_review = conf_score < 0.6

    validation = ValidationResult(
        is_valid=True,
        confidence_score=conf_score,
        warnings=[f"신뢰도 낮음 ({scoring_result.confidence}) - 수동 검토 권장"] if needs_review else [],
        errors=[],
        needs_human_review=needs_review,
    )

    status = AgentStatus.NEEDS_REVIEW if needs_review else AgentStatus.SUCCESS

    return AgentResult(
        agent_name="scoring_agent",
        status=status,
        data=scoring_result.model_dump(),
        validation=validation,
        processing_time_sec=elapsed,
        retry_count=retry_count,
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )
