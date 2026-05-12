"""Read-only TEP process knowledge search tool.

Wraps `EnhancedKnowledgeManager.search_knowledge` so the agent gets a stable,
structured shape to reason over. The retrieval method is keyword-based; we
do not call this 'semantic' or 'vector' search anywhere in the output.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .schemas import KnowledgeSearchResult, to_dict as _to_dict_helper

_KM = None  # lazy-init shared knowledge manager


def _get_km():
    global _KM
    if _KM is not None:
        return _KM
    # Local import to avoid circular import at package load time.
    from backend.knowledge_manager import EnhancedKnowledgeManager  # noqa: WPS433
    _KM = EnhancedKnowledgeManager()
    return _KM


def search_process_knowledge(query: str, max_results: int = 4) -> Dict[str, Any]:
    """Search the local TEP knowledge base and return ranked source excerpts.

    The result dict is intentionally LLM-friendly: a small list of dicts with
    `source_document`, `section`, `relevance_score`, and a short `excerpt`.
    """
    if not query or not query.strip():
        result = KnowledgeSearchResult(
            query="",
            excerpts=[],
            note="Empty query; nothing to search.",
        )
        return _to_dict(result)

    km = _get_km()
    chunks = km.search_knowledge(query, max_results=max_results)

    excerpts: List[Dict[str, Any]] = []
    for chunk in chunks:
        text = (chunk.content or "").strip().replace("\n", " ")
        if len(text) > 600:
            text = text[:597] + "..."
        excerpts.append({
            "source_document": chunk.source_document,
            "section": chunk.section,
            "relevance_score": round(float(chunk.relevance_score), 3),
            "excerpt": text,
        })

    result = KnowledgeSearchResult(
        query=query,
        excerpts=excerpts,
        note=("Keyword-based retrieval over RAG/converted_markdown. "
              "Not semantic / vector search."),
    )
    return _to_dict(result)


def _to_dict(model: Any) -> Dict[str, Any]:
    return _to_dict_helper(model)
