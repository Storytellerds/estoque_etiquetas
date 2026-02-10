def norm(text: str) -> str:
    return (text or "").strip().lower()


def contains(haystack: str, needle: str) -> bool:
    needle = norm(needle)
    if not needle:
        return True
    return needle in norm(haystack)


def ellipsize(text: str, max_len: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    if max_len <= 1:
        return "…"
    return text[: max_len - 1].rstrip() + "…"
