# design/

The product's design system is documented in **[`../DESIGN.md`](../DESIGN.md)** —
that file plus the live CSS tokens (`staticfiles/css/tokens.css`) are the single
source of truth.

## Why this folder is (almost) empty

It used to hold the original static mockup (`Exam GPT.dc.html` + `support.js`,
~120 KB). The implementation has since diverged from it, so the mockup was
**retired and deleted**: it had become stale enough to mislead new work and was
too large to read cheaply. Nothing references it anymore.

If you need a visual reference, run the app and look at the live screens — they
are the implementation of record. For the rules, read `DESIGN.md`.
