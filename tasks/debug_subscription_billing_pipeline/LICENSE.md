# Data License & Attribution

## Content

All code, data files, and case scenarios in this task are **fully synthetic** — hand-authored specifically for this evaluation. No real customer data, no real proprietary code, no scraped external content.

The scenarios are **inspired by** common patterns in SaaS subscription billing pipelines:
- Baked (historical, point-in-time) vs. live (current-state) fields diverging across reports
- Effective-date-based rate/price routing
- Percentage vs. fixed-dollar discount codes
- Grandfather pricing (a price change doesn't retroactively re-bill old invoices)
- Entity transfer (subscription reassigned to a different customer/region) cascading through multiple report views

But no specific real system was used as a template.

## License

The task (code, data, scenarios, judge, grader) is released under the same license as the trapstreet-tasks repo.

## Company / customer naming

Customer names (Acme Corp, Globex Ltd, Initech, Umbrella GmbH, Soylent Co, Hooli, Initrode Global) and IDs (`CUST-nnn`, `SUB-nnn`, `INV-nnnn`) are fictional and used purely as illustrative identifiers.
