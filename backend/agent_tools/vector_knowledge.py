"""Hybrid retrieval over the governed TEP knowledge base.

Substrates:
  - dense  : chromadb persistent collection backed by NIM nv-embedqa-e5-v5 (1024-d)
  - sparse : rank_bm25 BM25Okapi over the same chunked corpus
  - hybrid : Reciprocal Rank Fusion (RRF) of dense ⊕ sparse

Public API:
  build_or_load_index()               -> ensures the chroma collection + BM25 corpus exist
  hybrid_search(query, k=5)           -> list[dict] hits (RRF)
  dense_search(query, k=5)            -> list[dict] hits
  sparse_search(query, k=5)           -> list[dict] hits
  keyword_search(query, k=5)          -> falls through to the legacy keyword tool

The "wiki" layer in evidence_router.py uses hybrid_search by default; setting
TEP_WIKI_SUBSTRATE=keyword (env var) restores the old keyword path.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent.parent
_KB_DIR = _ROOT / "RAG" / "converted_markdown"
_CHROMA_DIR = _ROOT / "backend" / "data" / "embeddings" / "chroma"
_BM25_CACHE = _ROOT / "backend" / "data" / "embeddings" / "bm25_corpus.json"
_COLLECTION_NAME = "tep_wiki_v1"
_EMBED_MODEL = "nvidia/nv-embedqa-e5-v5"
_CHUNK_SIZE = 700        # characters
_CHUNK_OVERLAP = 120     # characters

# ---------------------------------------------------------------------------
# Module-level singletons (lazy)
# ---------------------------------------------------------------------------
_chroma_client = None
_chroma_collection = None
_bm25 = None
_bm25_doc_meta: List[Dict[str, Any]] = []  # parallel array of source/section info


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def _chunk_text(text: str, source: str) -> List[Dict[str, Any]]:
    """Split a markdown document into overlapping character windows.

    Each chunk records its source filename and the nearest preceding ## heading
    (if any) so the retriever can return human-readable citations.
    """
    chunks: List[Dict[str, Any]] = []
    # Track current section heading
    cur_section = ""
    # Walk by char windows but break at paragraph boundaries when possible
    n = len(text)
    i = 0
    while i < n:
        j = min(i + _CHUNK_SIZE, n)
        # try to extend to nearest newline for clean breaks
        if j < n:
            nl = text.find("\n\n", j - 80, j + 80)
            if nl != -1:
                j = nl
        chunk_text = text[i:j].strip()
        # find the most recent ## heading in this chunk for section context
        for m in re.finditer(r"(?m)^#{1,3}\s+(.+)$", text[:j]):
            cur_section = m.group(1).strip()[:120]
        if len(chunk_text) > 50:
            chunks.append(
                {
                    "id": f"{source}::{i}-{j}",
                    "text": chunk_text,
                    "source": source,
                    "section": cur_section,
                    "char_start": i,
                    "char_end": j,
                }
            )
        if j >= n:
            break
        i = max(0, j - _CHUNK_OVERLAP)
    return chunks


def _load_corpus() -> List[Dict[str, Any]]:
    """Chunk every markdown file in RAG/converted_markdown/."""
    corpus: List[Dict[str, Any]] = []
    if not _KB_DIR.exists():
        return corpus
    for md in sorted(_KB_DIR.glob("*.md")):
        try:
            text = md.read_text(errors="ignore")
        except Exception:
            continue
        corpus.extend(_chunk_text(text, md.name))
    return corpus


# ---------------------------------------------------------------------------
# Index build / load
# ---------------------------------------------------------------------------
def _get_embedder():
    """Return a NIM embedder. Raises on auth failure (caller can fall back)."""
    from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings  # noqa: WPS433
    return NVIDIAEmbeddings(
        model=_EMBED_MODEL,
        api_key=os.environ.get("NVIDIA_API_KEY", ""),
    )


def _ensure_chroma() -> Tuple[Any, Any]:
    """Create or open the persistent chroma collection."""
    global _chroma_client, _chroma_collection
    if _chroma_collection is not None:
        return _chroma_client, _chroma_collection
    import chromadb
    _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    _chroma_client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
    _chroma_collection = _chroma_client.get_or_create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return _chroma_client, _chroma_collection


def _ensure_bm25() -> Tuple[Any, List[Dict[str, Any]]]:
    """Build/load the BM25 index from the cached corpus."""
    global _bm25, _bm25_doc_meta
    if _bm25 is not None:
        return _bm25, _bm25_doc_meta

    if not _BM25_CACHE.exists():
        return None, []

    data = json.loads(_BM25_CACHE.read_text())
    _bm25_doc_meta = data["meta"]
    from rank_bm25 import BM25Okapi
    tokenized = [d["tokens"] for d in data["docs"]]
    _bm25 = BM25Okapi(tokenized)
    return _bm25, _bm25_doc_meta


def build_or_load_index(force_rebuild: bool = False) -> Dict[str, Any]:
    """Build chroma + BM25 indexes if missing; otherwise reuse persisted state."""
    global _bm25  # may need to reset cache after BM25 rebuild
    t0 = time.time()
    _, col = _ensure_chroma()

    needs_chroma_build = force_rebuild or col.count() == 0
    needs_bm25_build = force_rebuild or not _BM25_CACHE.exists()

    if not (needs_chroma_build or needs_bm25_build):
        # Both already exist
        _ensure_bm25()
        return {
            "status": "loaded_existing",
            "chunks_in_chroma": col.count(),
            "bm25_loaded": _bm25 is not None,
            "latency_ms": round((time.time() - t0) * 1000, 1),
        }

    corpus = _load_corpus()
    if not corpus:
        return {
            "status": "empty_corpus",
            "chunks_in_chroma": 0,
            "bm25_loaded": False,
            "latency_ms": round((time.time() - t0) * 1000, 1),
            "error": f"no markdown files in {_KB_DIR}",
        }

    # --- Build BM25 cache ---
    if needs_bm25_build:
        tokenized_docs = [
            {"id": c["id"], "tokens": re.findall(r"[a-z0-9]+", c["text"].lower())}
            for c in corpus
        ]
        meta = [
            {"id": c["id"], "source": c["source"], "section": c["section"],
             "text": c["text"]}
            for c in corpus
        ]
        _BM25_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _BM25_CACHE.write_text(json.dumps({"docs": tokenized_docs, "meta": meta}))
        # reset cache so next _ensure_bm25 picks up the new file
        _bm25 = None
        _ensure_bm25()

    # --- Build chroma index ---
    if needs_chroma_build:
        # Wipe any partial state
        if col.count() > 0 and force_rebuild:
            ids = col.get()["ids"]
            if ids:
                col.delete(ids=ids)
        try:
            embedder = _get_embedder()
        except Exception as exc:
            return {
                "status": "embed_init_failed",
                "error": f"{type(exc).__name__}: {exc}",
                "chunks_in_chroma": 0,
                "bm25_loaded": _bm25 is not None,
                "latency_ms": round((time.time() - t0) * 1000, 1),
            }

        # Embed in small batches (NIM has rate limits)
        BATCH = 16
        n = len(corpus)
        for i in range(0, n, BATCH):
            batch = corpus[i: i + BATCH]
            try:
                vecs = embedder.embed_documents([c["text"] for c in batch])
            except Exception as exc:
                # Continue with what we have; report partial
                return {
                    "status": "embed_partial_failure",
                    "error": f"batch {i}: {type(exc).__name__}: {exc}",
                    "chunks_in_chroma": col.count(),
                    "bm25_loaded": _bm25 is not None,
                    "latency_ms": round((time.time() - t0) * 1000, 1),
                }
            col.add(
                ids=[c["id"] for c in batch],
                embeddings=vecs,
                documents=[c["text"] for c in batch],
                metadatas=[
                    {"source": c["source"], "section": c["section"]}
                    for c in batch
                ],
            )

    return {
        "status": "built",
        "chunks_in_chroma": col.count(),
        "bm25_loaded": _bm25 is not None,
        "latency_ms": round((time.time() - t0) * 1000, 1),
    }


# ---------------------------------------------------------------------------
# Search functions
# ---------------------------------------------------------------------------
def dense_search(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """Vector search via chroma + NIM embeddings.

    Returns an empty list on embedding failure (e.g. NIM 401 / 429 / network).
    Earlier versions returned `[{"error": ...}]` which callers downstream
    treated as a "hit" with no text — the new contract is: hits[] is always
    a list of well-shaped hit dicts; nothing else.
    """
    _, col = _ensure_chroma()
    if col.count() == 0:
        return []
    try:
        emb = _get_embedder()
        qv = emb.embed_query(query)
    except Exception as exc:
        logger.warning("dense_search: embed failed (%s); returning []", exc)
        return []
    res = col.query(query_embeddings=[qv], n_results=k)
    hits: List[Dict[str, Any]] = []
    if not res.get("ids") or not res["ids"][0]:
        return hits
    for rank, (cid, doc, meta, dist) in enumerate(
        zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])
    ):
        hits.append({
            "id": cid,
            "source": meta.get("source", ""),
            "section": meta.get("section", ""),
            "text": doc,
            "score": float(1.0 - dist),  # cosine: 1=identical
            "rank": rank + 1,
            "substrate": "dense",
        })
    return hits


def sparse_search(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """BM25 over the same corpus."""
    bm25, meta = _ensure_bm25()
    if bm25 is None or not meta:
        return []
    q_tokens = re.findall(r"[a-z0-9]+", query.lower())
    scores = bm25.get_scores(q_tokens)
    # Top-k indices
    import numpy as np
    top = np.argsort(scores)[::-1][:k]
    hits: List[Dict[str, Any]] = []
    for rank, idx in enumerate(top):
        s = float(scores[idx])
        if s <= 0:
            continue
        m = meta[idx]
        hits.append({
            "id": m["id"],
            "source": m["source"],
            "section": m["section"],
            "text": m["text"],
            "score": s,
            "rank": rank + 1,
            "substrate": "sparse",
        })
    return hits


def hybrid_search(query: str, k: int = 5, rrf_k: int = 60) -> List[Dict[str, Any]]:
    """Reciprocal Rank Fusion of dense ⊕ sparse.

    RRF score = sum over substrates of 1 / (rrf_k + rank).
    """
    dense = dense_search(query, k=k * 2)
    sparse = sparse_search(query, k=k * 2)

    fused: Dict[str, Dict[str, Any]] = {}
    for hit in dense:
        if "error" in hit:
            continue
        cid = hit["id"]
        fused.setdefault(cid, {**hit, "rrf_score": 0.0,
                               "substrates": []})
        fused[cid]["rrf_score"] += 1.0 / (rrf_k + hit["rank"])
        fused[cid]["substrates"].append("dense")

    for hit in sparse:
        cid = hit["id"]
        if cid in fused:
            fused[cid]["rrf_score"] += 1.0 / (rrf_k + hit["rank"])
            fused[cid]["substrates"].append("sparse")
        else:
            fused[cid] = {**hit, "rrf_score": 1.0 / (rrf_k + hit["rank"]),
                          "substrates": ["sparse"]}

    ranked = sorted(fused.values(), key=lambda h: -h["rrf_score"])[:k]
    for r, h in enumerate(ranked, 1):
        h["rank"] = r
        h["substrate"] = "hybrid"
        h["score"] = h["rrf_score"]
    return ranked


def keyword_search(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """Legacy keyword path — delegates to existing search_process_knowledge."""
    from backend.agent_tools.knowledge_tools import search_process_knowledge
    raw = search_process_knowledge(query, max_results=k)
    excerpts = raw.get("excerpts", [])
    return [
        {
            "id": f"{e.get('source_document','')}::keyword::{i}",
            "source": e.get("source_document", ""),
            "section": e.get("section", ""),
            "text": e.get("excerpt", ""),
            "score": float(e.get("relevance_score", 0.0)),
            "rank": i + 1,
            "substrate": "keyword",
        }
        for i, e in enumerate(excerpts)
    ]
