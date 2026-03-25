"""
Simple language detector for zh/en based on character heuristics.
"""

import re
from typing import Literal


def detect_language(text: str) -> Literal["en", "zh"]:
    """
    Heuristic detection: if CJK characters ratio > 0.2 => zh else en.
    """
    if not text:
        return "en"
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    total = len(text)
    ratio = cjk / max(total, 1)
    return "zh" if ratio > 0.2 else "en"
