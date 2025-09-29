"""
apply_patch(parent_code, diff_json) → child_code

The diff JSON is expected to be the `.content` of the model reply, already
parsed with `json.loads(...)`.

Case A) {"code": "..."}      → return that full code directly
Case B) {"blocks": {...}}   → surgical replacement inside matching
                              EVOLVE-BLOCK regions.

Block detection uses regex – it remains robust to indentation changes.
"""

import re
from typing import Dict, Any

BLOCK_RE = re.compile(
    r"(^[ \t]*# === EVOLVE-BLOCK:\s*(?P<name>\w+).*?$\n)"  # head
    r"(?P<body>.*?)"  # body
    r"(?P<tail>^\s*# === END EVOLVE-BLOCK.*?$)",  # tail (was group(3), now named)
    re.M | re.S,
)


def apply_patch(parent_code: str, diff_json: Dict[str, Any]) -> str:
    # full overwrite
    if "code" in diff_json:
        return diff_json["code"]

    blocks: Dict[str, str] = diff_json.get("blocks", {})
    if not blocks:
        return parent_code  # nothing to do

    def _replace(match: re.Match) -> str:
        name = match.group("name")
        head = match.group(1)
        tail = match.group("tail")
        new_body = blocks.get(name)
        if new_body is None:
            return match.group(0)  # untouched
        # keep original indentation of the first line of body
        indent = re.match(r"^[ \t]*", match.group("body")).group(0)
        new_body_indented = (
            "\n".join(
                indent + line if line.strip() else line
                for line in new_body.rstrip().splitlines()
            )
            + "\n"
        )
        return head + new_body_indented + tail

    return BLOCK_RE.sub(_replace, parent_code)
