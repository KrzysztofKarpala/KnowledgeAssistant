from app.core.config import settings


def chunk_text(
    text: str,
    *,
    chunk_size: int = settings.chunk_size,
    chunk_overlap: int = settings.chunk_overlap,
) -> list[str]:
    normalized_text = text.strip()
    if not normalized_text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must not be negative.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")

    chunks: list[str] = []
    start = 0
    text_length = len(normalized_text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = normalized_text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end == text_length:
            break

        start = end - chunk_overlap

    return chunks
