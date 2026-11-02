from __future__ import annotations

import os
import tempfile
import unittest

from kavosh.styler import (
    generate_answer_key_pdf,
    generate_exam_docx,
    generate_exam_html,
    generate_exam_pdf,
    shape_persian,
)

SAMPLE_EXAM_MD = """# آزمون استاندارد زبان انگلیسی - پایه دوازدهم (Vision)

**مشخصات آزمون:** آموزشگاه: دبیرستان نمونه | طراح: گروه آموزشی | بارم کل: 2.00 نمره
---

## بخش اول: برگه سوالات دانش‌آموز (Student's Question Sheet)

### بخش دستور زبان (Grammar) — [2.00 Points]
**1. The ancient palace .......... two hundred years ago.** [Khordad 1404 — 1.00 نمره]
- a) was built
- b) is built
- c) built
- d) has built

**2. Children should respect their parents, ..........?** [Khordad 1404 — 1.00 نمره]
- a) shouldn't they
- b) should they
- c) don't they
- d) do they

---

## بخش دوم: کلید سوالات و راهنمای تصحیح رسمی (Official Scoring Key)
### بخش دستور زبان (Grammar) (بارم بخش: 2.00 نمره)
1. **a) was built** (1.00 نمره) [ریزبارم: choice: 1.00]
2. **a) shouldn't they** (1.00 نمره) [ریزبارم: choice: 1.00]
"""


class TestExamStyler(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.sample_md = os.path.join(self.tmp_dir.name, "sample_exam.md")
        with open(self.sample_md, "w", encoding="utf-8") as f:
            f.write(SAMPLE_EXAM_MD)
        self.out_docx = os.path.join(self.tmp_dir.name, "exam.docx")
        self.out_pdf = os.path.join(self.tmp_dir.name, "exam.pdf")
        self.out_html = os.path.join(self.tmp_dir.name, "exam.html")
        self.out_key_pdf = os.path.join(self.tmp_dir.name, "exam_key.pdf")

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_persian_shaping(self) -> None:
        shaped = shape_persian("به نام خدا")
        self.assertGreater(len(shaped), 0)

    def test_generate_exam_docx(self) -> None:
        generate_exam_docx(self.sample_md, self.out_docx)
        self.assertTrue(os.path.exists(self.out_docx))
        self.assertGreater(os.path.getsize(self.out_docx), 2000)

    def test_generate_exam_pdf(self) -> None:
        generate_exam_pdf(self.sample_md, self.out_pdf)
        self.assertTrue(os.path.exists(self.out_pdf))
        self.assertGreater(os.path.getsize(self.out_pdf), 10000)

    def test_generate_exam_html(self) -> None:
        generate_exam_html(self.sample_md, self.out_html)
        self.assertTrue(os.path.exists(self.out_html))
        self.assertGreater(os.path.getsize(self.out_html), 500)

    def test_generate_answer_key_pdf(self) -> None:
        generate_answer_key_pdf(self.sample_md, self.out_key_pdf)
        self.assertTrue(os.path.exists(self.out_key_pdf))
        self.assertGreater(os.path.getsize(self.out_key_pdf), 10000)


if __name__ == "__main__":
    unittest.main()
