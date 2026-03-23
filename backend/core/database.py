"""
SQLite DB 모듈 — CDP AI Platform
parse_sessions: PDF 파싱 세션 이력
questions:      추출된 문항 (세션별)
scoring_results: 채점 결과 (Phase 2)
"""
import sqlite3
import time
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from backend.core.config import settings

logger = logging.getLogger(__name__)

DB_PATH = settings.BASE_DIR / "data" / "cdp_platform.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """테이블 생성 (없으면)"""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS parse_sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT    NOT NULL,
                page_start  INTEGER,
                page_end    INTEGER,
                total_pages INTEGER,
                total_questions INTEGER DEFAULT 0,
                tables_extracted INTEGER DEFAULT 0,
                confidence_score REAL DEFAULT 0,
                status      TEXT    DEFAULT 'pending',
                created_at  TEXT    NOT NULL,
                processing_time_sec REAL
            );

            CREATE TABLE IF NOT EXISTS questions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   INTEGER NOT NULL REFERENCES parse_sessions(id) ON DELETE CASCADE,
                question_id  TEXT    NOT NULL,
                question_text TEXT   NOT NULL,
                guidance     TEXT,
                max_points   REAL,
                page_num     INTEGER,
                table_index  INTEGER,
                raw_text     TEXT,
                created_at   TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_questions_session ON questions(session_id);
            CREATE INDEX IF NOT EXISTS idx_questions_qid    ON questions(question_id);

            CREATE TABLE IF NOT EXISTS scoring_results (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id TEXT    NOT NULL,
                session_id  INTEGER REFERENCES parse_sessions(id),
                score       REAL    NOT NULL,
                max_score   REAL    NOT NULL,
                percentage  REAL    NOT NULL,
                deductions  TEXT,
                improvements TEXT,
                confidence  TEXT,
                answer_text TEXT,
                created_at  TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_scoring_qid ON scoring_results(question_id);
        """)
    logger.info(f"DB 초기화 완료: {DB_PATH}")


# ─────────────────────────────────────────
# parse_sessions CRUD
# ─────────────────────────────────────────

def create_session(
    source_file: str,
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
) -> int:
    """새 파싱 세션 생성 → session_id 반환"""
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO parse_sessions
               (source_file, page_start, page_end, status, created_at)
               VALUES (?, ?, ?, 'running', ?)""",
            (source_file, page_start, page_end, time.strftime("%Y-%m-%dT%H:%M:%S")),
        )
        return cur.lastrowid


def update_session(
    session_id: int,
    total_questions: int,
    tables_extracted: int,
    confidence_score: float,
    status: str,
    processing_time_sec: float,
    total_pages: Optional[int] = None,
) -> None:
    with get_db() as conn:
        conn.execute(
            """UPDATE parse_sessions
               SET total_questions=?, tables_extracted=?, confidence_score=?,
                   status=?, processing_time_sec=?, total_pages=?
               WHERE id=?""",
            (total_questions, tables_extracted, confidence_score,
             status, processing_time_sec, total_pages, session_id),
        )


def list_sessions(limit: int = 50) -> List[Dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, source_file, page_start, page_end, total_pages,
                      total_questions, tables_extracted, confidence_score,
                      status, created_at, processing_time_sec
               FROM parse_sessions ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_session(session_id: int) -> Optional[Dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM parse_sessions WHERE id=?", (session_id,)
        ).fetchone()
    return dict(row) if row else None


def delete_session(session_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM parse_sessions WHERE id=?", (session_id,))
    return cur.rowcount > 0


# ─────────────────────────────────────────
# questions CRUD
# ─────────────────────────────────────────

def save_questions(session_id: int, questions: List[Any]) -> int:
    """QuestionItem 리스트를 DB에 저장 → 저장 건수 반환"""
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    rows = [
        (
            session_id,
            q.question_id,
            q.question_text,
            q.guidance,
            q.max_points,
            q.page_num,
            q.table_index,
            q.raw_text,
            now,
        )
        for q in questions
    ]
    with get_db() as conn:
        conn.executemany(
            """INSERT INTO questions
               (session_id, question_id, question_text, guidance,
                max_points, page_num, table_index, raw_text, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
    return len(rows)


def list_questions(
    session_id: Optional[int] = None,
    question_id: Optional[str] = None,
    limit: int = 500,
    offset: int = 0,
) -> List[Dict]:
    sql = "SELECT * FROM questions WHERE 1=1"
    params: list = []
    if session_id is not None:
        sql += " AND session_id=?"
        params.append(session_id)
    if question_id:
        sql += " AND question_id LIKE ?"
        params.append(f"%{question_id}%")
    sql += " ORDER BY id ASC LIMIT ? OFFSET ?"
    params += [limit, offset]
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def count_questions(session_id: Optional[int] = None) -> int:
    sql = "SELECT COUNT(*) FROM questions"
    params: list = []
    if session_id is not None:
        sql += " WHERE session_id=?"
        params.append(session_id)
    with get_db() as conn:
        return conn.execute(sql, params).fetchone()[0]


# ─────────────────────────────────────────
# scoring_results CRUD
# ─────────────────────────────────────────

def save_scoring_result(
    question_id: str,
    score: float,
    max_score: float,
    percentage: float,
    deductions: str,
    improvements: str,
    confidence: str,
    answer_text: str,
    session_id: Optional[int] = None,
) -> int:
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO scoring_results
               (question_id, session_id, score, max_score, percentage,
                deductions, improvements, confidence, answer_text, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (question_id, session_id, score, max_score, percentage,
             deductions, improvements, confidence, answer_text,
             time.strftime("%Y-%m-%dT%H:%M:%S")),
        )
        return cur.lastrowid


def list_scoring_results(question_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
    sql = "SELECT * FROM scoring_results WHERE 1=1"
    params: list = []
    if question_id:
        sql += " AND question_id LIKE ?"
        params.append(f"%{question_id}%")
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


# DB 자동 초기화
init_db()
