"""Embedding generation and semantic search over the lore index.

Uses sentence-transformers (all-MiniLM-L6-v2) for semantic embeddings when
available. Falls back to a TF-IDF cosine similarity computed on the fly when
the model cannot be loaded (e.g. no network access for first-time download).
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from .config import memory_dir, load_config
from .store import list_memories

# Module-level caches — loaded once per process
_model = None
_use_tfidf: bool | None = None  # None = not yet decided


def _get_model(model_name: str, endpoint: str | None = None, ssl_verify: bool = True):
    """Return a SentenceTransformer model, or None if unavailable."""
    global _model, _use_tfidf
    if _use_tfidf:
        return None
    if _model is not None:
        return _model
    try:
        import logging
        import os
        import warnings

        # Kill all retry / SSL chatter before any imports touch the network
        for logger_name in (
            "huggingface_hub", "huggingface_hub.file_download",
            "huggingface_hub.utils", "sentence_transformers",
            "sentence_transformers.util", "urllib3", "urllib3.util.retry",
            "filelock", "tqdm",
        ):
            logging.getLogger(logger_name).setLevel(logging.CRITICAL)
        warnings.filterwarnings("ignore")

        # Disable tqdm progress bars globally
        import os
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        os.environ.setdefault("TQDM_DISABLE", "1")

        # -- Endpoint / mirror override (Artifactory, etc.) --
        if endpoint:
            os.environ["HF_ENDPOINT"] = endpoint.rstrip("/")

        # -- SSL verification override (scoped to this load only) --
        _orig_ssl_ctx = None
        if not ssl_verify:
            import ssl as _ssl_mod
            os.environ["CURL_CA_BUNDLE"] = ""
            os.environ["REQUESTS_CA_BUNDLE"] = ""
            _orig_ssl_ctx = _ssl_mod._create_default_https_context  # noqa: SLF001
            _ssl_mod._create_default_https_context = _ssl_mod._create_unverified_context  # noqa: SLF001

        from sentence_transformers import SentenceTransformer
        # Suppress the BERT LOAD REPORT printed to stdout/stderr
        import sys
        from io import StringIO
        _old_out, _old_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = StringIO()
        try:
            _model = SentenceTransformer(model_name)
        finally:
            sys.stdout, sys.stderr = _old_out, _old_err
            # Restore SSL context so later HTTPS calls in the process are unaffected
            if _orig_ssl_ctx is not None:
                import ssl as _ssl_mod
                _ssl_mod._create_default_https_context = _orig_ssl_ctx  # noqa: SLF001
        _use_tfidf = False
        return _model
    except Exception:
        _use_tfidf = True
        return None


# ---------------------------------------------------------------------------
# TF-IDF fallback
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _l2_norm(vec: list[float]) -> float:
    return math.sqrt(sum(v * v for v in vec))


def _normalize(vec: list[float]) -> list[float]:
    norm = _l2_norm(vec)
    return [v / norm for v in vec] if norm > 0 else vec


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _tfidf_vector(text: str, idf: dict[str, float]) -> list[float]:
    tokens = _tokenize(text)
    tf: dict[str, float] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    total = max(len(tokens), 1)
    vocab = list(idf)
    vec = [tf.get(w, 0) / total * idf.get(w, 0.0) for w in vocab]
    return _normalize(vec)


def _build_idf(corpus: list[str]) -> dict[str, float]:
    N = max(len(corpus), 1)
    df: dict[str, int] = {}
    for doc in corpus:
        for w in set(_tokenize(doc)):
            df[w] = df.get(w, 0) + 1
    return {w: math.log((N + 1) / (count + 1)) + 1 for w, count in df.items()}


def _index_path(root: Path) -> Path:
    return memory_dir(root) / "embeddings" / "index.json"


def _load_index(root: Path) -> list[dict[str, Any]]:
    path = _index_path(root)
    if path.exists():
        with path.open() as f:
            return json.load(f)
    return []


def _save_index(root: Path, index: list[dict[str, Any]]) -> None:
    path = _index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(index, f)


def _model_from_config(config: dict):
    """Load model using settings from lore config."""
    return _get_model(
        config.get("embedding_model", "all-MiniLM-L6-v2"),
        endpoint=config.get("model_endpoint"),
        ssl_verify=config.get("model_ssl_verify", True),
    )


def embed_text(root: Path, text: str) -> list[float]:
    """Return a normalized embedding vector for *text* (sentence-transformer or TF-IDF)."""
    config = load_config(root)
    model = _model_from_config(config)
    if model is not None:
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()
    # TF-IDF fallback: build IDF from all stored memories + the new text
    corpus = [m["content"] for m in list_memories(root)] + [text]
    idf = _build_idf(corpus)
    return _tfidf_vector(text, idf).tolist()


def index_memory(root: Path, mem_id: str, content: str) -> None:
    """Add or update the embedding for *mem_id* in the index.

    In TF-IDF fallback mode the index is skipped — search computes similarity
    on the fly over all memories instead.
    """
    config = load_config(root)
    model = _model_from_config(config)
    if model is None:
        return  # TF-IDF mode: no persistent index needed
    vector = model.encode(content, normalize_embeddings=True).tolist()
    index = _load_index(root)
    index = [e for e in index if e.get("id") != mem_id]
    index.append({"id": mem_id, "vector": vector})
    _save_index(root, index)


def batch_index_memories(root: Path, entries: list[tuple[str, str]]) -> None:
    """Encode and index multiple (id, content) pairs in one pass.

    Loads the model once, batch-encodes all texts, and writes index.json once.
    Much faster than calling index_memory() in a loop for N entries.
    In TF-IDF fallback mode this is a no-op (search is always on-the-fly).
    """
    if not entries:
        return
    config = load_config(root)
    model = _model_from_config(config)
    if model is None:
        return
    ids, texts = zip(*entries)
    vectors = model.encode(list(texts), normalize_embeddings=True, batch_size=32, show_progress_bar=False)
    index = _load_index(root)
    new_ids = set(ids)
    index = [e for e in index if e.get("id") not in new_ids]
    index.extend({"id": mid, "vector": vec.tolist()} for mid, vec in zip(ids, vectors))
    _save_index(root, index)


def rebuild_index(root: Path) -> int:
    """Rebuild the full embedding index from all stored memories."""
    memories = list_memories(root)
    config = load_config(root)
    model = _model_from_config(config)
    index = []
    if model is not None:
        texts = [m["content"] for m in memories]
        vectors = model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
        index = [{"id": m["id"], "vector": v.tolist()} for m, v in zip(memories, vectors)]
    else:
        # TF-IDF fallback
        corpus = [m["content"] for m in memories]
        idf = _build_idf(corpus)
        for mem in memories:
            vector = _tfidf_vector(mem["content"], idf).tolist()
            index.append({"id": mem["id"], "vector": vector})
    _save_index(root, index)
    return len(index)


def remove_from_index(root: Path, mem_id: str) -> None:
    """Remove *mem_id* from the embedding index."""
    index = _load_index(root)
    index = [e for e in index if e.get("id") != mem_id]
    _save_index(root, index)


def search(root: Path, query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """
    Semantic search: embed *query*, rank all memories by cosine similarity,
    and return the top_k results with an added '_score' key.

    When the embedding model is unavailable, uses TF-IDF cosine similarity
    computed over all stored memories.
    """
    memories = list_memories(root)
    if not memories:
        return []

    index = _load_index(root)
    config = load_config(root)
    model = _model_from_config(config)

    # If the index doesn't exist yet, build a transient one on the fly
    if not index:
        if model is not None:
            q_vec = list(model.encode(query, normalize_embeddings=True))
            texts = [m["content"] for m in memories]
            vecs = model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
            scored: list[tuple[float, str]] = [
                (_dot(q_vec, list(v)), m["id"])
                for m, v in zip(memories, vecs)
            ]
        else:
            corpus = [m["content"] for m in memories] + [query]
            idf = _build_idf(corpus)
            q_vec = _tfidf_vector(query, idf)
            scored = []
            for mem in memories:
                v = _tfidf_vector(mem["content"], idf)
                score = _dot(q_vec, v)
                scored.append((score, mem["id"]))
    else:
        if model is not None:
            q_vec = list(model.encode(query, normalize_embeddings=True))
        else:
            corpus = [m["content"] for m in memories] + [query]
            idf = _build_idf(corpus)
            q_vec = _tfidf_vector(query, idf)

        scored = []
        for entry in index:
            v = entry["vector"]
            score = _dot(q_vec, v)
            scored.append((score, entry["id"]))

    scored.sort(reverse=True)
    all_memories = {m["id"]: m for m in memories}
    results: list[dict[str, Any]] = []
    for score, mem_id in scored[:top_k]:
        mem = all_memories.get(mem_id)
        if mem:
            mem = dict(mem)
            mem["_score"] = round(score, 4)
            results.append(mem)
    return results
