# Build a pricing page

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

Everything else — layout, type, colour, copy — is yours.
