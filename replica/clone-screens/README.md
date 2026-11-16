# Build evidence

These are Traccia's own UI captures using an isolated archive with public/synthetic fixtures. No Plaud assets, personal recordings or tokens are included.

- `*-native.jpg`: complete native WebKit window screenshots, at 2× device resolution. Desktop captures are 2880 px wide (1440 logical window width); compact captures are 780 px wide (390 logical width).
- Other JPEGs: browser-visible fragments. The automation backend cropped screenshots even when full-page capture was requested; they are **not** full-width image-diff baselines. Their filename identifies the layout being inspected, not image dimensions.
- `viewport-report.json`: independently read CSS viewport/document widths inside an isolated responsive harness. Nine views were checked at 390/1440 px, with no document overflow.

There are no authenticated Plaud reference screenshots, so no original-versus-clone pixel-parity result is claimed. Use native captures for visual review; repeat standardized screenshots during replica-test before quantitative layout diffing. Some captures predate the final Q&A/export additions; the build log identifies the coverage.
