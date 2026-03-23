"""
답변 초안 Agent (Phase 3)
skills/draft_writing.skill.md 지침을 따름.
ChromaDB RAG + 크롤링 데이터 + Claude API로 고득점 답변 초안 생성.
"""
import time
import logging
from typing import List, Optional, Dict

from backend.core.models import AgentResult, AgentStatus, ValidationResult, CrawlResult
from backend.core.skill_loader import load_skill
from backend.core.llm_client import get_claude_client
from backend.core.vector_store import get_vector_store

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
MIN_DRAFT_LENGTH = 200  # 최소 답변 길이


def _build_context_from_rag(question_id: str, question_text: str, n_results: int = 5) -> str:
    """벡터 스토어에서 관련 Reference 데이터 검색"""
    store = get_vector_store()
    if store.count() == 0:
        return ""

    query = f"{question_id} {question_text}"
    docs = store.search(query, n_results=n_results)
    if not docs:
        return ""

    lines = ["[내부 Reference 데이터]"]
    for d in docs:
        source = d["metadata"].get("source", d["id"])
        lines.append(f"--- 출처: {source} ---")
        lines.append(d["text"][:800])  # 문서당 최대 800자
    return "\n".join(lines)


def _build_context_from_crawl(crawl_results: List[CrawlResult]) -> str:
    """크롤링 결과에서 컨텍스트 추출"""
    if not crawl_results:
        return ""

    lines = ["[외부 크롤링 데이터]"]
    for cr in crawl_results:
        if not cr.success or not cr.content:
            continue
        title = cr.title or cr.url
        lines.append(f"--- 출처: {title} ({cr.url}) ---")
        lines.append(cr.content[:600])  # 소스당 최대 600자
    return "\n".join(lines)


def _build_draft_prompt(
    question_id: str,
    question_text: str,
    max_points: float,
    company_data: Dict[str, str],
    rag_context: str,
    crawl_context: str,
) -> str:
    company_section = ""
    if company_data:
        company_section = "\n[회사 데이터]\n" + "\n".join(
            f"- {k}: {v}" for k, v in company_data.items()
        )

    context_section = ""
    if rag_context:
        context_section += f"\n{rag_context}"
    if crawl_context:
        context_section += f"\n{crawl_context}"

    return f"""다음 CDP 문항에 대한 고득점 답변 초안을 작성해주세요.

[문항 ID] {question_id}
[문항 내용] {question_text}
[배점] {max_points}점{company_section}{context_section}

작성 지침:
1. 위 데이터를 최대한 활용하고, 없는 수치는 "[데이터 필요]"로 표시
2. 완전성·정확성·일관성·구체성 4개 채점 카테고리 모두 충족
3. 최소 200자 이상, 배점에 비례해 상세도 조절
4. 출처 데이터 활용 시 출처 명시
5. 한국어로 작성, CDP 공식 용어(영문) 병기

아래 JSON 형식으로만 응답하세요:
{{
  "draft": "작성된 답변 전문",
  "data_sources_used": ["사용한 출처 목록"],
  "missing_data": ["추가로 필요한 데이터 항목"],
  "confidence": "높음|보통|낮음",
  "estimated_score_pct": <예상 득점 비율 0~100>
}}
"""


def _parse_draft_response(raw: str) -> Optional[dict]:
    import json
    try:
        text = raw.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            return None
        return json.loads(text[start:end])
    except Exception as e:
        logger.warning(f"초안 응답 파싱 실패: {e}")
        return None


def run_answer_draft_agent(
    question_id: str,
    question_text: str,
    max_points: float,
    company_data: Optional[Dict[str, str]] = None,
    crawl_results: Optional[List[CrawlResult]] = None,
) -> AgentResult:
    """
    CDP 문항 답변 초안 자동 생성.

    Args:
        question_id: 문항 ID (예: C1.1)
        question_text: 문항 내용
        max_points: 최고 배점
        company_data: 회사 특정 데이터 딕셔너리 (예: {"Scope1_배출량": "1,200 tCO2e"})
        crawl_results: 크롤 Agent에서 얻은 외부 데이터 (선택)

    Returns:
        AgentResult (data: {"draft": ..., "sources": ..., "missing_data": ..., "confidence": ...})
    """
    t_start = time.time()
    skill_text = load_skill("draft_writing")
    client = get_claude_client()

    # RAG 컨텍스트 빌드
    rag_context = _build_context_from_rag(question_id, question_text)
    crawl_context = _build_context_from_crawl(crawl_results or [])

    prompt = _build_draft_prompt(
        question_id=question_id,
        question_text=question_text,
        max_points=max_points,
        company_data=company_data or {},
        rag_context=rag_context,
        crawl_context=crawl_context,
    )

    parsed: Optional[dict] = None
    last_error = ""
    retry_count = 0

    for attempt in range(MAX_RETRIES + 1):
        try:
            raw = client.chat(
                prompt=prompt,
                system_prompt=skill_text,
                temperature=0.3,  # 초안은 약간 창의적으로
            )
            parsed = _parse_draft_response(raw)
            if parsed and len(parsed.get("draft", "")) >= MIN_DRAFT_LENGTH:
                break
            last_error = "초안 길이 부족 또는 파싱 실패"
        except Exception as e:
            last_error = str(e)
            logger.warning(f"초안 생성 시도 {attempt + 1} 실패: {e}")

        retry_count = attempt + 1
        if attempt < MAX_RETRIES:
            time.sleep(1)

    elapsed = round(time.time() - t_start, 2)

    if not parsed:
        return AgentResult(
            agent_name="answer_draft_agent",
            status=AgentStatus.FAILED,
            error_message=f"초안 생성 실패 ({MAX_RETRIES + 1}회 시도): {last_error}",
            processing_time_sec=elapsed,
            retry_count=retry_count,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

    conf_map = {"높음": 0.9, "보통": 0.7, "낮음": 0.45}
    confidence_str = parsed.get("confidence", "보통")
    conf_score = conf_map.get(confidence_str, 0.7)
    needs_review = conf_score < 0.6 or bool(parsed.get("missing_data"))

    warnings = []
    if parsed.get("missing_data"):
        warnings.append(f"누락 데이터: {', '.join(parsed['missing_data'][:3])}")

    validation = ValidationResult(
        is_valid=True,
        confidence_score=conf_score,
        warnings=warnings,
        errors=[],
        needs_human_review=needs_review,
    )

    result_data = {
        "question_id": question_id,
        "draft": parsed.get("draft", ""),
        "data_sources_used": parsed.get("data_sources_used", []),
        "missing_data": parsed.get("missing_data", []),
        "confidence": confidence_str,
        "estimated_score_pct": parsed.get("estimated_score_pct", 0),
        "rag_docs_used": store_count() if rag_context else 0,
        "crawl_sources_used": len([r for r in (crawl_results or []) if r.success]),
    }

    status = AgentStatus.NEEDS_REVIEW if needs_review else AgentStatus.SUCCESS

    return AgentResult(
        agent_name="answer_draft_agent",
        status=status,
        data=result_data,
        validation=validation,
        processing_time_sec=elapsed,
        retry_count=retry_count,
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )


def store_count() -> int:
    try:
        return get_vector_store().count()
    except Exception:
        return 0
