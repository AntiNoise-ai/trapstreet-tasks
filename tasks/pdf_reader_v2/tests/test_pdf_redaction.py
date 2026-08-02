"""The shipped PDF must contain no personal data — in its TEXT LAYER, not
just visually.

This is the regression guard for the defect this fork was built around: the
source document had black rectangles *painted over* names, addresses, emails
and phone numbers. Painting hides pixels. The text underneath stayed in the
content stream and came straight back out of `extract_text()`. Two further
pages had no box at all.

It reads as safe because the document's DocuSign font subset is shifted by
-29 codepoints, so raw extraction looks like mojibake. The shift auto-detects
in a few lines, which is what this module does before checking anything.

**Every assertion here is a pattern or an allowlist of non-sensitive values.**
There is deliberately no list of the personal tokens being excluded: this file
is public, and a denylist of names, streets and postcodes would republish in
plaintext exactly what the redaction removed from the PDF. The strongest check
below needs no such list anyway — it asserts that no text survives underneath
any black rectangle, which is the actual defect.

If these fail, the PDF has been replaced with an unredacted copy. Re-run
`tools/apply_redactions.py` — do not weaken the assertions.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

fitz = pytest.importorskip("fitz", reason="pymupdf not installed")

TASK = Path(__file__).parent.parent
PDF = TASK / "AST_Issue_1_CanaryWharf.pdf"
SHIFT = 29


def deshift(s: str) -> str:
    return "".join(
        chr(ord(c) + SHIFT) if 0x01 <= ord(c) <= 0x60 and ord(c) not in (9, 10, 13) else c
        for c in s
    )


@pytest.fixture(scope="module")
def doc():
    d = fitz.open(PDF)
    yield d
    d.close()


@pytest.fixture(scope="module")
def text(doc) -> str:
    return "\n".join(deshift(p.get_text()) for p in doc)


def test_shift_is_still_the_right_one(text):
    """Guards the guard: if the deshift stopped working, every assertion
    below would pass vacuously against mojibake."""
    common = sum(text.lower().count(w) for w in ("the", "tenant", "landlord", "rent"))
    assert common > 500, "deshift produced no readable English — the checks below prove nothing"


# ------------------------------------------------- the actual defect

def _black_boxes(page) -> list:
    out = []
    for d in page.get_drawings():
        f = d.get("fill")
        if f and f[0] < 0.15 and f[1] < 0.15 and f[2] < 0.15:
            r = d["rect"]
            if r.width >= 20 and r.height >= 5:
                out.append(r)
    return out


def test_no_text_survives_under_any_black_box(doc):
    """THE check. A redaction box that still has text under it is the exact
    bug this task forked to fix, and it needs no denylist to detect.

    Containment, not intersection: `get_textbox()` returns everything whose
    bbox merely *clips* the rect, which on a full-width box picks up the
    adjacent line and the field's own label. A word genuinely hidden under a
    box is contained by it, so require 80% of the word's area to be inside.
    """
    offenders = []
    for page in doc:
        boxes = _black_boxes(page)
        if not boxes:
            continue
        for x0, y0, x1, y1, word, *_ in page.get_text("words"):
            if not deshift(word).strip():
                continue
            wr = fitz.Rect(x0, y0, x1, y1)
            area = max(wr.get_area(), 0.01)
            if any((wr & b).get_area() / area > 0.8 for b in boxes if b.intersects(wr)):
                offenders.append(f"page {page.number + 1} at {(round(x0), round(y0))}")
    assert not offenders, (
        f"text is still extractable underneath {len(offenders)} black-box region(s): "
        f"{offenders[:5]} — the boxes are painted, not redacted"
    )


def test_the_document_still_has_its_redaction_boxes(doc):
    """Inverse of the above: a PDF with no black boxes at all would pass the
    previous test trivially."""
    total = sum(len(_black_boxes(p)) for p in doc)
    assert total >= 15, f"expected the redaction boxes to still be drawn, found {total}"


# ------------------------------------------------- pattern-based sweeps

def test_no_personal_mobile_number(text):
    assert not re.search(r"\b07\d{3}\s?\d{6}\b", text)


def test_no_personal_name_after_a_title(text):
    """The form the individuals' names appeared in throughout the document."""
    assert not re.findall(r"\b(?:Miss|Mrs|Ms|Mr)\s+[A-Z][a-z]+", text)


def test_no_residential_flat_address(text):
    """Both residential addresses were written as 'Flat <number>, …'. No
    business address in this document uses that form."""
    assert not re.search(r"\bFlat\s*\d", text)


# ------------------------------------------------- allowlists (public values only)

BUSINESS_EMAILS = {"Deposits@TenancyDepositscheme.com", "hello@ovoenergy.co.uk"}

# Letting agent, deposit scheme, energy supplier and the banks named in the
# deposit clause. All published business addresses.
BUSINESS_POSTCODES = {
    "BS1 6ED", "E14 5HP", "E14 8JH", "EC2V 7HN",
    "HP2 7TG", "NW1 3AN", "TW13 6LL", "W1K 3JL", "W5 5TH",
}


def test_only_business_email_addresses_remain(text):
    found = set(re.findall(r"[A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text))
    assert found <= BUSINESS_EMAILS, f"unexpected email(s) in the PDF: {found - BUSINESS_EMAILS}"


def test_only_business_postcodes_remain(text):
    found = set(re.findall(r"\b[A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][A-Z]{2}\b", text))
    assert found <= BUSINESS_POSTCODES, f"unexpected postcode(s): {found - BUSINESS_POSTCODES}"
    assert found, "no postcodes at all — the document was over-redacted"


# ------------------------------------------------- answers must survive

ANSWER_EVIDENCE = {
    "case_01/02 tiered rent": r"2100.*2400",
    "case_03 deposit": r"2,250",
    "case_04 start date": r"September\s*2022",
    "case_09 six-month extension": r"six.{0,2}month",
    "case_11 deposit scheme": r"Dispute Service|TDS",
    "case_12 pets": r"domestic animals",
    "case_13 first-year rent": r"1,950",
    # NB: don't anchor on "%". In this font subset the percent glyph encodes
    # from raw 0x20, which a uniform +29 deshift cannot tell apart from a real
    # space — "3%" comes back as "3=". Anchor on surrounding words instead.
    "case_14 late interest": r"rate of 3.{0,4}per annum.{0,40}base rate",
    "case_15 act + section": r"Section 19A of the Housing Act.{0,10}1988",
    "case_17 escalation": r"Independent Case Examiner|\bICE\b",
    "case_18 letting fee": r"13\.2",
    "case_18 inventory + admin": r"144.*480",
    "case_18 term length": r"36 months",
}


@pytest.mark.parametrize("name,pattern", sorted(ANSWER_EVIDENCE.items()))
def test_redaction_did_not_remove_answer_evidence(name, pattern, text):
    assert re.search(pattern, text, re.I | re.S), f"{name}: redaction ate a gold answer"
