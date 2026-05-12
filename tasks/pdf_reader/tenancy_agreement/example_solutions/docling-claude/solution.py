"""Docling + Claude agent — Docling extracts PDF → markdown, Claude answers from text.

Tests the "extract then ask" pattern with IBM's Docling (RapidOCR-backed).
Caches the parsed markdown locally between cases (same PDF for all 19 questions)
and uses Anthropic prompt caching to avoid re-charging for the markdown payload
on cases 2-N.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from anthropic import Anthropic
from docling.document_converter import DocumentConverter

MODEL = os.environ.get("MODEL", "claude-opus-4-7")
CACHE_DIR = Path("/tmp/trapstreet-docling-cache")

PRICES = {
    "claude-opus-4-7":    {"in": 15.00, "out": 75.00, "cache_read": 1.50,  "cache_write": 18.75},
    "claude-sonnet-4-6":  {"in":  3.00, "out": 15.00, "cache_read": 0.30,  "cache_write":  3.75},
}


SYSTEM = """You answer questions from a UK Assured Shorthold Tenancy (AST) agreement
that has been converted to markdown. The conversion may have minor OCR errors.

Rules:
- Answer ONLY based on what the markdown says — no general knowledge fill-in.
- Answer the question literally and completely. If the question has multiple parts, answer ALL parts.
- Follow any format constraint stated in the question (e.g. "DD/MM/YYYY", "yes/no", "GBP amount").
- Do not hedge. Do not say "I cannot determine" if the answer is in the document.
- Be terse — one short sentence is usually right.
"""


def extract_markdown(pdf_path: Path) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha1(pdf_path.read_bytes()).hexdigest()[:16]
    cache_file = CACHE_DIR / f"{h}.md"
    if cache_file.exists():
        return cache_file.read_text()
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    markdown = result.document.export_to_markdown()
    cache_file.write_text(markdown)
    return markdown


def estimate_cost_usd(usage, model: str) -> float:
    p = PRICES.get(model)
    if not p:
        return 0.0
    cw = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cr = getattr(usage, "cache_read_input_tokens", 0) or 0
    in_ = getattr(usage, "input_tokens", 0) or 0
    out = getattr(usage, "output_tokens", 0) or 0
    return round((in_ * p["in"] + cw * p["cache_write"] + cr * p["cache_read"] + out * p["out"]) / 1_000_000, 6)


def main() -> int:
    inputs = json.loads(os.environ["INPUTS"])
    outputs = json.loads(os.environ.get("OUTPUTS", "{}"))
    question = Path(inputs["question.txt"]).read_text().strip()
    markdown = extract_markdown(Path(inputs["document.pdf"]))

    client = Anthropic(max_retries=10)  # absorb transient 429/529 with backoff
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Document (extracted by Docling):\n\n{markdown}",
                    "cache_control": {"type": "ephemeral"},  # cache markdown across cases
                },
                {"type": "text", "text": f"\n---\n\nQuestion: {question}\n\nAnswer:"},
            ],
        }],
    )

    answer = next((b.text for b in msg.content if b.type == "text"), "").strip()
    print(answer)

    if "usage.json" in outputs:
        u = msg.usage
        usage_record = {
            "model": MODEL,
            "input_tokens": getattr(u, "input_tokens", 0),
            "output_tokens": getattr(u, "output_tokens", 0),
            "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
            "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
            "usd_cost": estimate_cost_usd(u, MODEL),
        }
        Path(outputs["usage.json"]).write_text(json.dumps(usage_record, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
