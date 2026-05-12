"""Marker + Claude agent — Marker extracts PDF → markdown, Claude answers from the text.

Marker is the OSS competitor to Docling; uses a layout-aware vision-LLM pipeline
internally. Same caching strategy as docling-claude — the AST PDF is identical
across all 22 cases.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

# Force CPU — Marker's Surya models exceed 9GB MPS limit on Apple Silicon.
# CPU is slower but doesn't OOM. Set before any torch import.
os.environ.setdefault("TORCH_DEVICE", "cpu")
os.environ.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.0")

from anthropic import Anthropic

MODEL = os.environ.get("MODEL", "claude-opus-4-7")
CACHE_DIR = Path("/tmp/trapstreet-marker-cache")


SYSTEM = """You answer questions from a UK Assured Shorthold Tenancy (AST) agreement
that has been converted to markdown. The conversion may have minor errors.

Rules:
- Answer ONLY based on what the markdown says — no general knowledge fill-in.
- Answer the question literally and completely. If the question has multiple parts, answer ALL parts.
- Follow any format constraint stated in the question (e.g. "DD/MM/YYYY", "yes/no", "GBP amount").
- Do not hedge. Do not say "I cannot determine" if the answer is in the document.
- Be terse — one short sentence is usually right.
"""


def extract_markdown(pdf_path: Path) -> str:
    """Convert PDF to markdown via Marker. Caches by content hash."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha1(pdf_path.read_bytes()).hexdigest()[:16]
    cache_file = CACHE_DIR / f"{h}.md"
    if cache_file.exists():
        return cache_file.read_text()

    # Imports inside the function — Marker is heavy (loads model weights);
    # we want the import to happen on first call, not at module load.
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import text_from_rendered

    converter = PdfConverter(artifact_dict=create_model_dict())
    rendered = converter(str(pdf_path))
    markdown, _meta, _images = text_from_rendered(rendered)
    cache_file.write_text(markdown)
    return markdown


def main() -> int:
    inputs = json.loads(os.environ["INPUTS"])
    question = Path(inputs["question.txt"]).read_text().strip()
    markdown = extract_markdown(Path(inputs["document.pdf"]))

    client = Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"Document (extracted by Marker):\n\n{markdown}\n\n"
                f"---\n\nQuestion: {question}\n\nAnswer:"
            ),
        }],
    )

    answer = next((b.text for b in msg.content if b.type == "text"), "").strip()
    print(answer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
