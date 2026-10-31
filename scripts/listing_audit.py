"""Conservative checks for KDP listing fields.

These checks flag common issues for human review. They do not rank keywords,
predict sales, choose categories, or guarantee KDP approval.
"""

from __future__ import annotations

import re


def _normalise(value: str) -> str:
    return " ".join(value.casefold().split())


def audit_listing(description: str, keywords: list, categories: list) -> list[str]:
    """Return actionable listing warnings without modifying user-supplied text."""
    warnings: list[str] = []

    if not description.strip():
        warnings.append("description is empty")
    if len(description.strip()) > 4000:
        warnings.append(
            f"description has {len(description.strip()):,} characters; "
            "the configured KDP limit is 4,000"
        )

    if len(keywords) > 7:
        warnings.append(f"{len(keywords)} keyword entries supplied; the configured limit is 7")
    if len(categories) > 3:
        warnings.append(f"{len(categories)} categories supplied; the configured limit is 3")

    seen: dict[str, int] = {}
    category_words = {
        word
        for category in categories
        if isinstance(category, str)
        for word in re.findall(r"[\w]+", category.casefold())
    }

    for index, raw in enumerate(keywords, 1):
        if not isinstance(raw, str):
            warnings.append(f"keyword {index} is not text")
            continue
        keyword = raw.strip()
        if not keyword:
            warnings.append(f"keyword {index} is empty")
            continue

        normalised = _normalise(keyword)
        if normalised in seen:
            warnings.append(
                f"keyword {index} duplicates keyword {seen[normalised]}: {keyword!r}"
            )
        else:
            seen[normalised] = index

        if '"' in keyword or "'" in keyword:
            warnings.append(
                f"keyword {index} contains quotation marks; review KDP's keyword guidance"
            )

        overlap = sorted(set(re.findall(r"[\w]+", normalised)) & category_words)
        if overlap:
            warnings.append(
                f"keyword {index} repeats category word(s): {', '.join(overlap)}"
            )

        if re.search(r"\b(?:best|bestselling|#1)\b", normalised):
            warnings.append(
                f"keyword {index} may contain a promotional/ranking claim: {keyword!r}"
            )
        if re.search(r"\b(?:new|latest|today|20\d{2})\b", normalised):
            warnings.append(
                f"keyword {index} may be time-sensitive: {keyword!r}"
            )

    for index, category in enumerate(categories, 1):
        if not isinstance(category, str) or not category.strip():
            warnings.append(f"category {index} is empty or is not text")

    return warnings
