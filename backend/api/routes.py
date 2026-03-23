"""FastAPI 라우터 - CDP AI Platform API"""
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

from backend.core.config import settings
from backend.core.skill_loader import list_available_skills
from backend.agents.pdf_parser_agent import run_pdf_parser
from backend.agents.crawl_agent import run_crawl_agent

router = APIRouter(prefix="/api/v1")


# ─────────────────────────────────
# 시스템 상태
# ─────────────────────────────────
@router.get("/health")
def health_check():
    """서버 상태 및 설정 확인"""
    config_errors = settings.validate()
    return {
        "status": "ok" if not config_errors else "degraded",
        "claude_api": {
            "model": settings.CLAUDE_MODEL,
            "key_configured": bool(settings.ANTHROPIC_API_KEY),
            "key_preview": (settings.ANTHROPIC_API_KEY[:12] + "...") if settings.ANTHROPIC_API_KEY else "미설정",
        },
        "skills_loaded": list_available_skills(),
        "config_errors": config_errors,
    }


# ─────────────────────────────────
# PDF Parser Agent
# ─────────────────────────────────
@router.post("/parse-pdf")
async def parse_pdf(
    file: UploadFile = File(...),
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
):
    """CDP 가이드 PDF 업로드 → 문항+테이블 추출 및 Excel 저장.
    page_start/page_end 로 페이지 범위 지정 가능 (대용량 분할 처리)."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다")

    save_path = settings.UPLOAD_DIR / file.filename
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    result = run_pdf_parser(
        pdf_path=str(save_path),
        output_dir=str(settings.OUTPUT_DIR),
        save_excel=True,
        page_start=page_start,
        page_end=page_end,
    )
    return result.model_dump()


# ─────────────────────────────────
# Crawl Agent
# ─────────────────────────────────
class CrawlRequest(BaseModel):
    urls: List[str]
    query: str = "CDP ESG 정보"
    use_playwright: bool = False
    summarize: bool = True


@router.post("/crawl")
def crawl(req: CrawlRequest):
    """ESG/CDP 관련 외부 URL 크롤링 + Claude 요약"""
    if not req.urls:
        raise HTTPException(status_code=400, detail="URL 목록이 비어있습니다")
    result = run_crawl_agent(
        urls=req.urls,
        query=req.query,
        use_playwright=req.use_playwright,
        summarize=req.summarize,
    )
    return result.model_dump()


# ─────────────────────────────────
# 파일 관리
# ─────────────────────────────────
@router.get("/outputs")
def list_outputs():
    """생성된 결과 파일 목록"""
    settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = [
        {"name": f.name, "size_kb": round(f.stat().st_size / 1024, 1)}
        for f in settings.OUTPUT_DIR.iterdir() if f.is_file()
    ]
    return {"files": files}


@router.get("/download/{filename}")
def download_file(filename: str):
    """결과 파일 다운로드"""
    file_path = settings.OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"파일 없음: {filename}")
    return FileResponse(path=str(file_path), filename=filename)


# ============================================================
# Phase 2: Scoring Agent
# ============================================================
from backend.agents.scoring_agent import run_scoring_agent

class ScoreRequest(BaseModel):
    question_id: str
    question_text: str
    answer_text: str
    max_points: float
    reference_data: str = None

@router.post("/score")
def score_answer(req: ScoreRequest):
    """CDP 답변 자동 채점 (Phase 2)"""
    if not req.answer_text.strip():
        raise HTTPException(status_code=400, detail="답변 내용이 비어있습니다")
    if req.max_points <= 0:
        raise HTTPException(status_code=400, detail="배점은 0보다 커야 합니다")
    result = run_scoring_agent(
        question_id=req.question_id,
        question_text=req.question_text,
        answer_text=req.answer_text,
        max_points=req.max_points,
        reference_data=req.reference_data,
    )
    return result.model_dump()


# ============================================================
# Phase 3: Answer Draft Agent
# ============================================================
from backend.agents.answer_draft_agent import run_answer_draft_agent
from backend.core.vector_store import get_vector_store

class DraftRequest(BaseModel):
    question_id: str
    question_text: str
    max_points: float
    company_data: dict = {}

@router.post("/draft-answer")
def draft_answer(req: DraftRequest):
    """CDP 문항 답변 초안 자동 생성 (Phase 3)"""
    if not req.question_text.strip():
        raise HTTPException(status_code=400, detail="문항 내용이 비어있습니다")
    result = run_answer_draft_agent(
        question_id=req.question_id,
        question_text=req.question_text,
        max_points=req.max_points,
        company_data=req.company_data,
    )
    return result.model_dump()


@router.post("/reference/upload")
async def upload_reference(file: UploadFile = File(...)):
    """Reference 문서를 RAG 벡터 스토어에 추가 (Phase 3)"""
    if not file.filename.lower().endswith((".txt", ".md")):
        raise HTTPException(status_code=400, detail=".txt 또는 .md 파일만 지원합니다")
    content = (await file.read()).decode("utf-8", errors="ignore")
    store = get_vector_store()
    ok = store.add_document(
        doc_id=file.filename,
        text=content,
        metadata={"source": file.filename, "type": "uploaded"},
    )
    if not ok:
        raise HTTPException(status_code=500, detail="문서 저장 실패")
    return {"message": f"{file.filename} 저장 완료", "total_docs": store.count()}


@router.get("/reference/status")
def reference_status():
    """RAG 벡터 스토어 상태 확인"""
    store = get_vector_store()
    return {
        "total_docs": store.count(),
        "chromadb_active": store.is_chromadb_active(),
    }



# ============================================================
# DB 조회 / 배치 파싱 엔드포인트
# ============================================================
from backend.core.database import (
    list_sessions, get_session, delete_session,
    list_questions, count_questions, list_scoring_results,
)

@router.get("/sessions")
def get_sessions(limit: int = 50):
    return {"sessions": list_sessions(limit=limit)}

@router.get("/sessions/{session_id}")
def get_session_detail(session_id: int):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"세션 없음: {session_id}")
    questions = list_questions(session_id=session_id, limit=1000)
    return {"session": session, "questions": questions}

@router.delete("/sessions/{session_id}")
def remove_session(session_id: int):
    if not delete_session(session_id):
        raise HTTPException(status_code=404, detail=f"세션 없음: {session_id}")
    return {"message": f"세션 {session_id} 삭제 완료"}

@router.get("/questions")
def get_questions(
    session_id: Optional[int] = None,
    question_id: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
):
    questions = list_questions(session_id=session_id, question_id=question_id, limit=limit, offset=offset)
    total = count_questions(session_id=session_id)
    return {"total": total, "count": len(questions), "questions": questions}

@router.get("/scoring-history")
def get_scoring_history(question_id: Optional[str] = None, limit: int = 100):
    return {"results": list_scoring_results(question_id=question_id, limit=limit)}

class BatchParseRequest(BaseModel):
    filename: str
    page_start: Optional[int] = None
    page_end:   Optional[int] = None

@router.post("/parse-pdf/batch")
def parse_pdf_batch(req: BatchParseRequest):
    save_path = settings.UPLOAD_DIR / req.filename
    if not save_path.exists():
        raise HTTPException(status_code=404, detail=f"파일 없음: {req.filename}. 먼저 /parse-pdf로 업로드하세요.")
    if req.page_start and req.page_end and req.page_start > req.page_end:
        raise HTTPException(status_code=400, detail="page_start가 page_end보다 클 수 없습니다")
    result = run_pdf_parser(
        pdf_path=str(save_path),
        output_dir=str(settings.OUTPUT_DIR),
        save_excel=True,
        page_start=req.page_start,
        page_end=req.page_end,
    )
    return result.model_dump()

