"""
Vector Store (Phase 3) — ChromaDB 기반 RAG
회사 Reference 문서를 저장하고 문항별로 관련 내용을 검색한다.
"""
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    logger.warning("chromadb 미설치. RAG 기능 비활성화. pip install chromadb 로 설치하세요.")

from backend.core.config import settings


# ChromaDB 컬렉션 이름
COLLECTION_NAME = "cdp_reference"


class VectorStore:
    """
    회사 Reference 문서 저장 및 의미 기반 검색.
    chromadb가 없으면 키워드 폴백 모드로 동작.
    """

    def __init__(self):
        self._client = None
        self._collection = None
        self._fallback_docs: List[dict] = []  # chromadb 없을 때 메모리 저장

        if HAS_CHROMADB:
            self._init_chromadb()

    def _init_chromadb(self):
        try:
            db_path = str(settings.BASE_DIR / "data" / "vector_db")
            Path(db_path).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=db_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"ChromaDB 초기화 완료: {db_path}")
        except Exception as e:
            logger.error(f"ChromaDB 초기화 실패 (폴백 모드로 전환): {e}")
            self._client = None
            self._collection = None

    def add_document(self, doc_id: str, text: str, metadata: Optional[dict] = None) -> bool:
        """
        문서를 벡터 스토어에 추가.

        Args:
            doc_id: 고유 문서 ID
            text: 문서 텍스트
            metadata: 태그, 출처, 날짜 등 선택적 메타데이터

        Returns:
            성공 여부
        """
        meta = metadata or {}

        if self._collection is not None:
            try:
                self._collection.upsert(
                    ids=[doc_id],
                    documents=[text],
                    metadatas=[meta],
                )
                return True
            except Exception as e:
                logger.error(f"문서 추가 실패 ({doc_id}): {e}")
                return False
        else:
            # 폴백: 메모리 저장
            self._fallback_docs = [d for d in self._fallback_docs if d["id"] != doc_id]
            self._fallback_docs.append({"id": doc_id, "text": text, "metadata": meta})
            return True

    def search(self, query: str, n_results: int = 5) -> List[dict]:
        """
        쿼리와 의미적으로 유사한 문서 검색.

        Args:
            query: 검색 쿼리
            n_results: 반환할 최대 결과 수

        Returns:
            [{"id": ..., "text": ..., "metadata": ..., "distance": ...}, ...]
        """
        if self._collection is not None:
            try:
                count = self._collection.count()
                if count == 0:
                    return []
                actual_n = min(n_results, count)
                results = self._collection.query(
                    query_texts=[query],
                    n_results=actual_n,
                )
                output = []
                ids = results.get("ids", [[]])[0]
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0]
                for i, doc_id in enumerate(ids):
                    output.append({
                        "id": doc_id,
                        "text": docs[i] if i < len(docs) else "",
                        "metadata": metas[i] if i < len(metas) else {},
                        "distance": distances[i] if i < len(distances) else 1.0,
                    })
                return output
            except Exception as e:
                logger.error(f"벡터 검색 실패: {e}")
                return []
        else:
            # 폴백: 키워드 매칭
            query_lower = query.lower()
            scored = []
            for doc in self._fallback_docs:
                text_lower = doc["text"].lower()
                score = sum(1 for w in query_lower.split() if w in text_lower)
                if score > 0:
                    scored.append((score, doc))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [
                {"id": d["id"], "text": d["text"], "metadata": d["metadata"], "distance": 1.0 / (s + 1)}
                for s, d in scored[:n_results]
            ]

    def load_reference_dir(self) -> int:
        """
        data/reference/ 폴더의 텍스트 파일을 자동 로드.

        Returns:
            로드된 문서 수
        """
        ref_dir = settings.REFERENCE_DIR
        if not ref_dir.exists():
            return 0

        count = 0
        for f in ref_dir.iterdir():
            if f.suffix in (".txt", ".md"):
                try:
                    text = f.read_text(encoding="utf-8")
                    self.add_document(
                        doc_id=f.stem,
                        text=text,
                        metadata={"source": f.name, "type": "reference"},
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"참고 파일 로드 실패 ({f.name}): {e}")
        if count:
            logger.info(f"Reference 문서 {count}개 로드 완료")
        return count

    def count(self) -> int:
        """저장된 문서 수"""
        if self._collection is not None:
            return self._collection.count()
        return len(self._fallback_docs)

    def is_chromadb_active(self) -> bool:
        return self._collection is not None


# 싱글턴
_store: Optional["VectorStore"] = None


def get_vector_store() -> "VectorStore":
    global _store
    if _store is None:
        _store = VectorStore()
        _store.load_reference_dir()
    return _store
