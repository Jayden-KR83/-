# -*- coding: utf-8 -*-
"""
Question Structurer Module
PDF Parser Agent가 추출한 raw elements를 질문 단위로 구조화하는 모듈.

_extract_page_elements()에서 나온 element 리스트를 받아서
각 질문별로 Question Details, Numbered Columns, Requested Content, Tags를 분류한다.
"""

import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PATTERNS
# ---------------------------------------------------------------------------
# matches (0.2), (1.1), (C1.1), (C1.1a), (3.2.1) etc
SECTION_PATTERN = re.compile(r"^\(([A-Za-z]?\d+(?:\.\d+[a-z]?)*)\)\s*(.*)")
# matches C1.1, W2.3a, C1.1.1 etc at line start
QUESTION_ID_PATTERN = re.compile(
    r"^([A-Z]\d+\.\d+[a-z]?(?:\.\d+)?)\s+(.*)"
)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def _clean_cell(value) -> str:
    """셀 값 정리. None, nan, none은 빈 문자열로 변환."""
    if value is None:
        return ""
    s = str(value).strip()
    if s.lower() in ("nan", "none"):
        return ""
    # 셀 내부 줄바꿈은 공백으로 치환
    s = s.replace("\n", " ").replace("\r", " ")
    return s


def _flatten_table(table_data):
    """
    2D 테이블 데이터를 읽기 쉬운 텍스트로 변환.

    각 셀은 ' | '로 연결하고, 각 행은 줄바꿈으로 구분한다.
    완전히 빈 행은 건너뛴다.
    """
    if not table_data:
        return ""

    lines = []
    for row in table_data:
        if row is None:
            continue
        cleaned = [_clean_cell(c) for c in row]
        # 완전히 빈 행 건너뛰기
        if not any(cleaned):
            continue
        lines.append(" | ".join(cleaned))

    return "\n".join(lines)


def _classify_table(table_data):
    """
    테이블의 첫 번째 비어있지 않은 셀을 기반으로 테이블 유형을 분류.

    Returns:
        str: 'question_details', 'numbered_columns', 'requested_content',
             'tags', 또는 'unknown'
    """
    if not table_data:
        return "unknown"

    # 첫 번째 비어있지 않은 셀 찾기
    first_cell = ""
    for row in table_data:
        if row is None:
            continue
        for cell in row:
            val = _clean_cell(cell)
            if val:
                first_cell = val
                break
        if first_cell:
            break

    if not first_cell:
        return "unknown"

    first_lower = first_cell.lower()

    # Question details 테이블
    if "question detail" in first_lower:
        return "question_details"

    # Tags 테이블
    if "tag" in first_lower:
        return "tags"

    # Requested content 테이블
    if "requested" in first_lower or "content" in first_lower:
        return "requested_content"

    # 숫자 헤더 (컬럼 정의 테이블) - 첫 셀이 숫자인 경우
    if first_cell.strip().isdigit():
        return "numbered_columns"

    return "unknown"


def _find_question_in_text(text):
    """
    텍스트에서 질문 패턴을 찾는다.

    Returns:
        tuple: (질문번호, 질문내용) 또는 None
    """
    if not text:
        return None

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # (X.X) 패턴 체크
        m_section = SECTION_PATTERN.match(line)
        if m_section:
            sec_num = "(%s)" % m_section.group(1)
            content = m_section.group(2).strip()
            return (sec_num, content)

        # C1.1 스타일 패턴 체크
        m_qid = QUESTION_ID_PATTERN.match(line)
        if m_qid:
            qid = m_qid.group(1)
            content = m_qid.group(2).strip()
            return (qid, content)

    return None


def _has_question_pattern(text):
    """텍스트에 질문 패턴이 포함되어 있는지 확인."""
    return _find_question_in_text(text) is not None


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------
def structure_questions(elements):
    """
    elements 리스트를 순회하며 질문 단위로 구조화된 데이터를 생성한다.

    Args:
        elements: _extract_page_elements()의 반환값.
            각 element는 다음 형태:
            {"type": "text"|"table", "page": N, "data": ..., "y_top": float}

    Returns:
        list of dict: 각 질문별 구조화된 데이터.
            {
                "질문번호": "(1.1)",
                "질문내용": "In which language...",
                "페이지": 12,
                "Question_Details": "...",
                "Numbered_Columns": "...",
                "Requested_Content": "...",
                "Tags": "...",
            }
        별도로 pre_questions 리스트도 반환 (첫 질문 이전의 테이블들).

    실제 반환값은 dict:
        {
            "pre_questions": [...],
            "questions": [...]
        }
    """
    if not elements:
        return {"pre_questions": [], "questions": []}

    pre_questions = []  # 첫 질문 이전의 테이블들
    questions = []      # 구조화된 질문 리스트
    current_question = None

    for elem in elements:
        elem_type = elem.get("type", "")
        elem_data = elem.get("data", "")
        elem_page = elem.get("page", 0)

        if elem_type == "text":
            # 텍스트에서 질문 패턴 찾기
            question_info = _find_question_in_text(elem_data)

            if question_info is not None:
                # 이전 질문이 있으면 저장
                if current_question is not None:
                    questions.append(current_question)

                q_num, q_content = question_info
                current_question = {
                    "질문번호": q_num,
                    "질문내용": q_content,
                    "페이지": elem_page,
                    "Question_Details": "",
                    "Numbered_Columns": "",
                    "Requested_Content": "",
                    "Tags": "",
                }
            else:
                # 질문 패턴이 아닌 텍스트는 현재 질문의 내용에 추가할 수도 있음
                # (질문 본문이 여러 줄에 걸쳐 있는 경우)
                if current_question is not None:
                    # 질문 내용이 비어있지 않고 추가 텍스트가 있으면 연결
                    extra_text = elem_data.strip()
                    if extra_text and current_question["질문내용"]:
                        current_question["질문내용"] = (
                            "%s %s" % (current_question["질문내용"], extra_text)
                        )
                    elif extra_text:
                        current_question["질문내용"] = extra_text

        elif elem_type == "table":
            table_data = elem_data

            if current_question is None:
                # 첫 질문 이전의 테이블 -> pre_questions에 저장
                pre_questions.append({
                    "페이지": elem_page,
                    "테이블": _flatten_table(table_data),
                })
                continue

            # 테이블 분류
            tbl_type = _classify_table(table_data)
            flattened = _flatten_table(table_data)

            if not flattened.strip():
                continue

            if tbl_type == "question_details":
                if current_question["Question_Details"]:
                    current_question["Question_Details"] = (
                        "%s\n%s" % (
                            current_question["Question_Details"], flattened
                        )
                    )
                else:
                    current_question["Question_Details"] = flattened

            elif tbl_type == "numbered_columns":
                if current_question["Numbered_Columns"]:
                    current_question["Numbered_Columns"] = (
                        "%s\n%s" % (
                            current_question["Numbered_Columns"], flattened
                        )
                    )
                else:
                    current_question["Numbered_Columns"] = flattened

            elif tbl_type == "requested_content":
                # Requested content 테이블은 여러 페이지에 걸쳐 분할될 수 있음
                if current_question["Requested_Content"]:
                    current_question["Requested_Content"] = (
                        "%s\n%s" % (
                            current_question["Requested_Content"], flattened
                        )
                    )
                else:
                    current_question["Requested_Content"] = flattened

            elif tbl_type == "tags":
                if current_question["Tags"]:
                    current_question["Tags"] = (
                        "%s\n%s" % (current_question["Tags"], flattened)
                    )
                else:
                    current_question["Tags"] = flattened

            else:
                # 분류 불가 테이블 -> Requested_Content에 추가
                # (연속 테이블이나 보충 내용일 가능성 높음)
                if current_question["Requested_Content"]:
                    current_question["Requested_Content"] = (
                        "%s\n%s" % (
                            current_question["Requested_Content"], flattened
                        )
                    )
                else:
                    current_question["Requested_Content"] = flattened

    # 마지막 질문 저장
    if current_question is not None:
        questions.append(current_question)

    logger.info(
        "질문 구조화 완료: %d개 질문, %d개 사전 테이블",
        len(questions), len(pre_questions)
    )

    return {
        "pre_questions": pre_questions,
        "questions": questions,
    }
