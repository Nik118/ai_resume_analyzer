import torch
from sentence_transformers import SentenceTransformer, util

# Load a small, fast sentence-transformer model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Cache for candidate embeddings to avoid re-encoding on every rank request
# Key: candidate_id (int), Value: torch.Tensor
_EMBEDDING_CACHE = {}


def rank_candidates(
    job_description: str, jd_skills: list[str], candidates: list[dict]
) -> list[dict]:
    """
    Ranks candidates based on the cosine similarity between their extracted text
    (or skills) and the job description. Also calculates pros and cons based on skills.

    candidates: list of dicts, e.g., [{"id": 1, "text": "...", "skills": [...]}]
    """
    if not candidates:
        return []

    # Encode the job description
    jd_embedding = model.encode(job_description, convert_to_tensor=True)

    # Optimize: Encode only the candidates that are not in cache
    embeddings_list = []
    texts_to_encode = []
    indices_to_encode = []

    for i, c in enumerate(candidates):
        cid = c["id"]
        if cid in _EMBEDDING_CACHE:
            embeddings_list.append(_EMBEDDING_CACHE[cid])
        else:
            embeddings_list.append(None)  # Placeholder
            texts_to_encode.append(c["text"])
            indices_to_encode.append(i)

    # Batch encode missing candidates
    if texts_to_encode:
        new_embeddings = model.encode(texts_to_encode, convert_to_tensor=True)
        for idx, new_emb in zip(indices_to_encode, new_embeddings):
            _EMBEDDING_CACHE[candidates[idx]["id"]] = new_emb
            embeddings_list[idx] = new_emb

    # Stack all embeddings into a single tensor for vectorized similarity computation
    candidate_embeddings = torch.stack(embeddings_list)

    # Compute cosine similarities
    cosine_scores = util.cos_sim(jd_embedding, candidate_embeddings)[0]

    jd_skills_set = set(jd_skills)

    ranked_candidates = []
    for idx, score in enumerate(cosine_scores):
        c = candidates[idx].copy()
        c["score"] = float(score)

        c_skills_set = set(c.get("skills", []))

        c["pros"] = list(c_skills_set.intersection(jd_skills_set))
        c["cons"] = list(jd_skills_set.difference(c_skills_set))

        # Remove redundant text block from response dict to save memory/bandwidth
        c.pop("text", None)

        ranked_candidates.append(c)

    # Sort by score descending
    ranked_candidates.sort(key=lambda x: x["score"], reverse=True)

    return ranked_candidates
