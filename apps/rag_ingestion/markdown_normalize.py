from __future__ import annotations

import re


_DISPLAY_MATH_RE = re.compile(r"\$\$[\s\S]*?\$\$")
_INLINE_MATH_RE = re.compile(r"(?<![A-Za-z\\])\$([^\n$]+?)\$")


def _convert_inline_math_outside_display_blocks(text: str) -> str:
    parts: list[str] = []
    cursor = 0

    for match in _DISPLAY_MATH_RE.finditer(text):
        parts.append(_convert_inline_math_segment(text[cursor : match.start()]))
        parts.append(match.group(0))
        cursor = match.end()

    parts.append(_convert_inline_math_segment(text[cursor:]))
    return "".join(parts)


def _convert_inline_math_segment(segment: str) -> str:
    def replace(match: re.Match[str]) -> str:
        math = match.group(1).strip()
        if not math:
            return match.group(0)
        return rf"\({math}\)"

    return _INLINE_MATH_RE.sub(replace, segment)


def normalize_extracted_markdown(value: object) -> object:
    if not isinstance(value, str):
        return value
    return _convert_inline_math_outside_display_blocks(value)
