from __future__ import annotations

import re

_DISPLAY_MATH_RE = re.compile(r"\$\$[\s\S]*?\$\$")
_FENCED_CODE_RE = re.compile(r"(?:^|\n)(?:```.*?\n[\s\S]*?\n```)(?=\n|$)", re.MULTILINE)
_INLINE_CODE_RE = re.compile(r"(?P<ticks>`+)[^`\n]*?(?P=ticks)")
_INLINE_MATH_RE = re.compile(r"(?<![A-Za-z\\])\$([^\n$]+?)\$")
_PROTECTED_BLOCK_RE = re.compile(
    "|".join([
        _DISPLAY_MATH_RE.pattern,
        _FENCED_CODE_RE.pattern,
        _INLINE_CODE_RE.pattern,
    ]),
    re.MULTILINE,
)


def _convert_inline_math_outside_protected_blocks(text: str) -> str:
    parts: list[str] = []
    cursor = 0

    for match in _PROTECTED_BLOCK_RE.finditer(text):
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
    return _convert_inline_math_outside_protected_blocks(value)
