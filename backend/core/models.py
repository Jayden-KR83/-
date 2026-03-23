"""CDP AI Platform - 공통 데이터 모델"""
from pydantic import BaseModel
from typing import Any, Optional, List
from enum import Enum


class AgentStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class ValidationResult(BaseModel):
    is_valid: bool
    confidence_score: float  # 0.0 ~ 1.0
    warnings: List[str] = []
    errors: List[str] = []
    needs_human_review: bool = False


class AgentResult(BaseModel):
    agent_name: str
    status: AgentStatus
    data: Optional[Any] = None
    validation: Optional[ValidationResult] = None
    error_message: Optional[str] = None
    processing_time_sec: Optional[float] = None
    created_at: str = ""
    retry_count: int = 0


class QuestionItem(BaseModel):
    question_id: str
    question_text: str
    guidance: Optional[str] = None
    max_points: Optional[float] = None
    page_num: Optional[int] = None
    table_index: Optional[int] = None
    raw_text: Optional[str] = None


class PDFParseResult(BaseModel):
    source_file: str
    total_questions: int
    questions: List[QuestionItem]
    tables_extracted: int
    parse_warnings: List[str] = []


class CrawlResult(BaseModel):
    url: str
    title: Optional[str] = None
    content: str
    links: List[str] = []
    crawled_at: str = ""
    success: bool = True
    error: Optional[str] = None


class DeductionItem(BaseModel):
    category: str
    reason: str
    points_deducted: float


class ScoringResult(BaseModel):
    question_id: str
    score: float
    max_score: float
    percentage: float
    deductions: List[DeductionItem] = []
    improvements: List[str] = []
    confidence: str
