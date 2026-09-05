# One screen for a charity's trustees

Riverbank Trust runs three food banks. Its five trustees look at the numbers
once a month, for maybe two minutes, on whatever device is to hand. They are not
analysts. What they need to leave with is a feeling about whether things are all
right, and to notice the one thing that is not.

Build that screen from this data:

```json
{
  "months": ["Mar","Apr","May","Jun","Jul","Aug"],
  "donations_gbp": [41200, 38900, 40100, 36400, 31800, 24600],
  "meals_served":  [8100, 8400, 8800, 9200, 9900, 10600],
  "regular_donors": [612, 605, 598, 571, 549, 502],
  "sites": [
    {"name": "Eastgate", "meals": 4200, "volunteers": 31, "stock_weeks": 1.2},
    {"name": "Harlow Road", "meals": 3900, "volunteers": 18, "stock_weeks": 3.4},
    {"name": "Pike Street", "meals": 2500, "volunteers": 9,  "stock_weeks": 0.6}
  ]
}
```

Donations are falling while demand rises. Pike Street has under a week of stock
and nine volunteers. Whether and how that lands is up to you.

## The only fixed requirements

One self-contained HTML file, printed to stdout and nothing else — no prose, no
fences. Nothing loaded from off the page: no external stylesheets, scripts,
fonts or images. It must not throw, and it must work at 375px wide as well as on
a desktop.

Everything else — structure, layout, type, colour, copy, what to leave out — is
your call. There is no hidden checklist. You are being read by someone deciding
whether this is good work.
