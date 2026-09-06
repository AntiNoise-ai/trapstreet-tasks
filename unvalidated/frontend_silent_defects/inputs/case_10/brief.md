# Build a pricing page, and keep it small

One self-contained HTML file. Print it to stdout and nothing else — no prose,
no fences, no explanation.

## Content

A pricing page for a SaaS product: a heading, one line of supporting copy, a
monthly/annual billing switch, three plan tiers, and a "contact sales" form
with an email field.

## Requirements

**1. Render the tiers from `window.__DATA__`.** If `window.__DATA__` is an
array, use it; otherwise fall back to your own three plans. Each entry is
`{ name, monthly, features: [] }`. Annual price is the monthly price × 10.

**2. Expose these hooks**, so the page can be driven:

| hook | on |
|---|---|
| `data-testid="billing-monthly"` | the monthly control |
| `data-testid="billing-toggle"` | the annual control |
| `data-testid="tier"` | each plan card |
| `data-testid="price"` | the price inside each card |
| `data-testid="email"` | the email input |

**3. Stay inside the budget.** The finished page must come in under all three
of these, and they are checked:

| ceiling | limit |
|---|---|
| DOM elements | **70** |
| CSS rules | **42** |
| source bytes | **10,500** |

For scale: pages built to this same brief with no budget stated run 67–119
elements, 39–61 rules and 9,475–16,473 bytes. The budget is reachable — one page
in eighteen hit all three without trying — but nothing reaches it by accident.

Everything else — layout, type, colour, copy — is yours. Cutting a requirement
to fit is not a way to make the budget.
