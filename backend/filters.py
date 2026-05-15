from config import SMATA_CORE_TERMS

def calculate_relevance_score(text: str):
    """
    Lógica de scoring:
    - Base: 0 puntos
    - +10 por cada término de inclusión encontrado en text (case-insensitive)
    - -20 por cada término de exclusión encontrado
    - Score final: clamp(score, 0, 100)
    """
    if not text:
        return 0, []

    text_lower = text.lower()
    score = 0
    matched_terms = []

    # Inclusión
    for term in SMATA_CORE_TERMS["inclusion"]:
        if term.lower() in text_lower:
            score += 10
            matched_terms.append(term)

    # Exclusión
    for term in SMATA_CORE_TERMS["exclusion"]:
        if term.lower() in text_lower:
            score -= 20

    # Clamp 0-100
    final_score = max(0, min(100, score))
    
    return final_score, matched_terms

def filter_posts(posts, strict_mode: bool = False):
    """
    Strict Mode activo: descartar posts con score < 50
    Strict Mode inactivo: mostrar todos, ordenados por score desc
    """
    results = []
    for post in posts:
        score, terms = calculate_relevance_score(post.get("text", ""))
        post["relevance_score"] = score
        post["matched_terms"] = terms
        
        if strict_mode and score < 50:
            continue
            
        results.append(post)
    
    # Sort by relevance desc
    return sorted(results, key=lambda x: x["relevance_score"], reverse=True)
