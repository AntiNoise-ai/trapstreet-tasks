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

**3. The data is not friendly.** `window.__DATA__` is whatever the caller
passes: it may be empty, hold one plan or fifty, carry a plan name hundreds of
characters long or written right-to-left, carry a price of zero, a negative
price, or a nine-digit one, and may be missing `features` entirely. The page
must render without throwing and without breaking its layout in every one of
those cases. Treat plan names as text, never as markup.

Everything else — layout, type, colour, copy — is yours.
