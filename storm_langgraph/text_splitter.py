from __future__ import annotations


SEPARATORS = [
    "\n\n",
    "\n",
    ".",
    "\uff0e",
    "\u3002",
    ",",
    "\uff0c",
    "\u3001",
    " ",
    "\u200b",
    "",
]


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    text = text or ""
    if len(text) <= chunk_size:
        return [text] if text else []

    chunks: list[str] = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(text_len, start + chunk_size)
        candidate = text[start:end]
        split_point = None
        for separator in SEPARATORS:
            if not separator:
                continue
            idx = candidate.rfind(separator)
            if idx > chunk_size // 3:
                split_point = start + idx + len(separator)
                break
        final_end = split_point or end
        chunk = text[start:final_end].strip()
        if chunk:
            chunks.append(chunk)
        if final_end >= text_len:
            break
        start = max(start + 1, final_end - chunk_overlap)
    return chunks

