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

**3.** The product is called **Meridian**, and it is sold to mid-market
logistics operators in the EU and UK. Our brand palette is built around
`#1D4ED8`, with `#0F172A` for text and `#F8FAFC` for surfaces; the type is a
system sans stack. Procurement teams at this size usually evaluate three
vendors in parallel and sign in Q4, so the page tends to be read alongside two
competitors' pages in adjacent tabs. Marketing would like the tone to be
plain and unhurried rather than urgent.

Everything else — layout, type, colour, copy — is yours.
