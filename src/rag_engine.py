from functools import lru_cache


@lru_cache(maxsize=1)
def _get_embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("all-MiniLM-L6-v2")


def build_lever_index(lever_library: list[dict]):
    """Build FAISS index from lever descriptions and metadata."""
    import faiss

    texts = []
    for lever in lever_library:
        parts = [
            lever.get("title", ""),
            lever.get("description", ""),
            " ".join(lever.get("category_targets", [])),
            " ".join(lever.get("scope_targets", [])),
            " ".join(lever.get("evidence_snippets", [])),
        ]
        texts.append(" ".join(p for p in parts if p))

    model = _get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    embeddings = embeddings.astype("float32")

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    id_to_lever = {i: lever for i, lever in enumerate(lever_library)}
    return index, id_to_lever


def search_levers(
    query: str,
    sector: str,
    hotspots: list[str],
    index,
    id_to_lever: dict,
    top_k: int = 10,
) -> list[dict]:
    """Search for relevant levers using RAG."""
    model = _get_embedding_model()
    prompt = f"{query} sector: {sector} hotspots: {', '.join(hotspots)}"
    query_embedding = model.encode([prompt]).astype("float32")
    distances, indices = index.search(query_embedding, top_k)
    results: list[dict] = []
    for rank, idx in enumerate(indices[0]):
        if idx == -1:
            continue
        lever = id_to_lever.get(int(idx))
        if lever:
            results.append({**lever, "score": float(distances[0][rank])})
    return results
