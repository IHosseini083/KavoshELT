# DESIGN-vision.md

Project extension of DESIGN.md for the Vision Curriculum Validator (vision.v1x.ir).

## Design Read & Dials
Reading this as: Curriculum Validation Web Tool for Iranian English Teachers, in a calm RTL-first deep-navy/light surface language, dial ENERGY 1 / RHYTHM 2 / MOTION 1.

## One-Line Decision Log (R-31)
- Color palette: Deep navy (#0E1522) and soft slate (#E9EFF5) with #6FD0A0/#187A50 green for in-syllabus validity and #7F9BFF/#3D5FD6 blue for out-of-syllabus attention items, avoiding harsh red alarmism while keeping >= 4.5:1 WCAG AA contrast.
- Typography: Embedded Vazirmatn (weights 400, 700, 800) so Persian UI labels, Persian numerals, and bilingual diagnostics render with consistent metrics across all OSes.
- Layout: Asymmetric two-column flex workspace on desktop (input editor card on inline-start, live diagnostic card on inline-end) that stacks cleanly into a single column below 768px (RHYTHM 2).
- Spacing: 4px base scale (4, 8, 12, 16, 24, 32, 48) using CSS logical properties (padding-inline, margin-block) for true RTL structure.
- Cards & Rows: Tone-stepped elevation (--bg to --surface to --surface-inset) with 1px solid var(--border) and zero dark-mode drop shadows to keep focus on the highlighted English text.
- Icons: Minimal inline SVG outline glyphs (aria-hidden="true") paired with visible text labels; no decorative AI sparkles or stock icon libraries.

## Project Components
1. Scope Selector Bar: Pill selects for Grade (پایه هفتم to پایه دوازدهم) and Maximum Lesson (درس ۱ to درس ۸), plus a secondary pill button to load a real textbook passage.
2. Annotated Text Preview: LTR block inside --surface-inset where out-of-syllabus words receive the .token-attention treatment (underline + pill badge on click/focus) and clicking a suggested synonym replaces the word in the editor.
3. Syllabus Coverage Strip: Segmented indicator showing the ratio of in-syllabus words (--accent-green segments) to total words (--fill-muted segments).
4. Diagnostic Inset Rows:
   - Out-of-syllabus word row uses .row.attention with diagonal blue stripes, a badge showing which future grade teaches the word (or خارج از کتاب), and clickable pill buttons for in-syllabus synonym replacements.
   - Grammar violation row uses .row.attention with the matched clause and Persian pedagogical explanation.
