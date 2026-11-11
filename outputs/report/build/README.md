# Report build

1. `python prep_tables.py <project_root> tables.json` reads `outputs/tables/*` and `data_clean/*` (no hand-typed numbers) and writes the table cells.
2. `node build_report.js tables.json <project_root>/outputs/figures/eda/eda3_tesg_vs_sa.png ../RA_report_FC_ESG_TWSE_food.docx` builds the Word report (needs the npm package `docx`).

Prose numbers were checked against the output files on 2026-11-07 (rebuilt after winsorizing TESG/E/S/G and adding RE) (every decimal in the text matches an output value, except 8.57, the SA turning point 0.737 / (2 x 0.043)).
