"""
Knowledge Processor — 다양한 파일 형식에서 텍스트 추출
지원: PDF, Excel, Word, PPT, Text, CSV, Markdown
"""
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    '.pdf': 'PDF 문서',
    '.xlsx': 'Excel 스프레드시트',
    '.xls': 'Excel 스프레드시트',
    '.docx': 'Word 문서',
    '.pptx': 'PowerPoint 프레젠테이션',
    '.txt': '텍스트 파일',
    '.csv': 'CSV 데이터',
    '.md': 'Markdown 문서',
}


def extract_text(file_path: str) -> List[Dict[str, Any]]:
    """
    파일에서 텍스트를 추출하여 청크 리스트로 반환.
    Returns: [{"text": str, "page": int, "source": str}, ...]
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == '.pdf':
        return _extract_pdf(file_path)
    elif ext in ('.xlsx', '.xls'):
        return _extract_excel(file_path)
    elif ext == '.docx':
        return _extract_word(file_path)
    elif ext == '.pptx':
        return _extract_ppt(file_path)
    elif ext in ('.txt', '.md'):
        return _extract_text(file_path)
    elif ext == '.csv':
        return _extract_csv(file_path)
    else:
        raise ValueError(f"지원하지 않는 파일 형식: {ext}")


def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """텍스트를 overlap이 있는 청크로 분할"""
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap
    return chunks


def _extract_pdf(file_path: str) -> List[Dict]:
    try:
        import pdfplumber
        chunks = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                for chunk in _chunk_text(text):
                    chunks.append({"text": chunk, "page": page_num, "source": Path(file_path).name})
        return chunks
    except Exception as e:
        logger.error(f"PDF 추출 실패: {e}")
        return []


def _extract_excel(file_path: str) -> List[Dict]:
    try:
        import pandas as pd
        chunks = []
        xl = pd.ExcelFile(file_path)
        for sheet_idx, sheet_name in enumerate(xl.sheet_names, 1):
            df = xl.parse(sheet_name, dtype=str).fillna("")
            # Convert sheet to readable text
            lines = [f"[시트: {sheet_name}]"]
            # Add headers
            lines.append(" | ".join(str(c) for c in df.columns))
            # Add rows
            for _, row in df.iterrows():
                row_text = " | ".join(str(v) for v in row.values if str(v).strip())
                if row_text.strip():
                    lines.append(row_text)
            sheet_text = "\n".join(lines)
            for chunk in _chunk_text(sheet_text):
                chunks.append({"text": chunk, "page": sheet_idx, "source": Path(file_path).name})
        return chunks
    except Exception as e:
        logger.error(f"Excel 추출 실패: {e}")
        return []


def _extract_word(file_path: str) -> List[Dict]:
    try:
        from docx import Document
        doc = Document(file_path)
        chunks = []
        full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        # Also extract tables
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    full_text += "\n" + row_text
        for i, chunk in enumerate(_chunk_text(full_text)):
            chunks.append({"text": chunk, "page": i + 1, "source": Path(file_path).name})
        return chunks
    except Exception as e:
        logger.error(f"Word 추출 실패: {e}")
        return []


def _extract_ppt(file_path: str) -> List[Dict]:
    try:
        from pptx import Presentation
        prs = Presentation(file_path)
        chunks = []
        for slide_num, slide in enumerate(prs.slides, 1):
            texts = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    texts.append(shape.text.strip())
            slide_text = "\n".join(texts)
            for chunk in _chunk_text(slide_text):
                chunks.append({"text": chunk, "page": slide_num, "source": Path(file_path).name})
        return chunks
    except Exception as e:
        logger.error(f"PPT 추출 실패: {e}")
        return []


def _extract_text(file_path: str) -> List[Dict]:
    try:
        text = Path(file_path).read_text(encoding='utf-8', errors='replace')
        return [{"text": chunk, "page": i + 1, "source": Path(file_path).name}
                for i, chunk in enumerate(_chunk_text(text))]
    except Exception as e:
        logger.error(f"텍스트 추출 실패: {e}")
        return []


def _extract_csv(file_path: str) -> List[Dict]:
    try:
        import pandas as pd
        df = pd.read_csv(file_path, dtype=str).fillna("")
        lines = [" | ".join(str(c) for c in df.columns)]
        for _, row in df.iterrows():
            row_text = " | ".join(str(v) for v in row.values if str(v).strip())
            if row_text.strip():
                lines.append(row_text)
        text = "\n".join(lines)
        return [{"text": chunk, "page": i + 1, "source": Path(file_path).name}
                for i, chunk in enumerate(_chunk_text(text))]
    except Exception as e:
        logger.error(f"CSV 추출 실패: {e}")
        return []
