"""Lightweight RAG: keyword search over text/PDF docs in kb_docs/.

No heavy vector DB needed for the MVP. Drop any .txt, .md or .pdf files
about Ghana agriculture into app/kb_docs/ and they become queryable.

Swap in llama-index/ChromaDB later if you want semantic search over a
large knowledge base — the query_knowledge_base() signature stays the same.
"""
import os
import re

from app import config


def _load_texts() -> list[tuple[str, str]]:
    texts = []
    if not config.KB_DIR.exists():
        return texts
    for fname in os.listdir(config.KB_DIR):
        path = config.KB_DIR / fname
        try:
            if fname.lower().endswith((".txt", ".md")):
                texts.append((fname, path.read_text(encoding="utf-8", errors="ignore")))
            elif fname.lower().endswith(".pdf"):
                from pypdf import PdfReader
                reader = PdfReader(str(path))
                texts.append((fname, "\n".join(page.extract_text() or "" for page in reader.pages)))
        except Exception:  # noqa: BLE001
            continue
    return texts


def _chunk(text: str, size: int = 800) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size)]


def query_knowledge_base(question: str, top_k: int = 2) -> str:
    """Return the most relevant KB passages for a question ('' if none)."""
    try:
        docs = _load_texts()
        if not docs:
            return ""
        q_words = set(re.findall(r"[a-z]+", question.lower()))
        scored = []
        for fname, text in docs:
            for i, chunk in enumerate(_chunk(text)):
                words = set(re.findall(r"[a-z]+", chunk.lower()))
                score = len(q_words & words)
                if score > 0:
                    scored.append((score, f"[{fname}] {chunk.strip()}"))
        scored.sort(key=lambda x: -x[0])
        return "\n\n".join(c for _, c in scored[:top_k])
    except Exception:  # noqa: BLE001
        return ""