def estimate_tokens(text):
    """Estimate token count. ~3.5 chars per token for code."""
    if not text:
        return 0
    return max(1, int(len(text) / 3.5))


def fits_budget(text, budget):
    """Check if text fits within a token budget."""
    return estimate_tokens(text) <= budget


def truncate_to_budget(text, budget):
    """Truncate text to fit within a token budget."""
    if fits_budget(text, budget):
        return text
    char_limit = int(budget * 3.5)
    return text[:char_limit]
