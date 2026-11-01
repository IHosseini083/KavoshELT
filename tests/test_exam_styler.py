import os
import shutil
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from exam_styler import (
    generate_exam_docx,
    generate_exam_pdf,
    generate_answer_key_pdf,
    shape_persian,
)
from exam_generator import generate_full_exam_package
from schema import init_db
from seed_all_grades import seed_curriculum


class TestExamStyler(unittest.TestCase):
    def setUp(self):
        self.sample_exam_md = (
            "/home/ubuntu/آزمون_شنیداری_زبان_انگلیسی_پایه_دهم_نوبت_اول.md"
        )
        self.out_docx = "/tmp/test_exam.docx"
        self.out_pdf = "/tmp/test_exam.pdf"
        self.out_key_pdf = "/tmp/test_exam_key.pdf"
        self.out_pkg_dir = "/tmp/test_exam_pkg"

    def test_persian_shaping(self):
        shaped = shape_persian("به نام خدا")
        self.assertTrue(len(shaped) > 0)

    def test_generate_exam_docx(self):
        if not os.path.exists(self.sample_exam_md):
            self.skipTest("Sample exam md not found")
        generate_exam_docx(self.sample_exam_md, self.out_docx)
        self.assertTrue(os.path.exists(self.out_docx))
        self.assertGreater(os.path.getsize(self.out_docx), 2000)

    def test_generate_exam_pdf(self):
        if not os.path.exists(self.sample_exam_md):
            self.skipTest("Sample exam md not found")
        generate_exam_pdf(self.sample_exam_md, self.out_pdf)
        self.assertTrue(os.path.exists(self.out_pdf))
        self.assertGreater(
            os.path.getsize(self.out_pdf), 10000
        )  # Embedded Vazirmatn font

    def test_generate_answer_key_pdf(self):
        if not os.path.exists(self.sample_exam_md):
            self.skipTest("Sample exam md not found")
        generate_answer_key_pdf(self.sample_exam_md, self.out_key_pdf)
        self.assertTrue(os.path.exists(self.out_key_pdf))
        self.assertGreater(os.path.getsize(self.out_key_pdf), 10000)

    def test_generate_full_exam_package_grade7(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        seed_curriculum(conn)
        res = generate_full_exam_package(
            conn, grade=7, term=1, out_dir=self.out_pkg_dir
        )
        conn.close()
        self.assertTrue(os.path.exists(res["markdown"]))
        self.assertTrue(os.path.exists(res["student_pdf"]))
        self.assertTrue(os.path.exists(res["student_docx"]))
        self.assertTrue(os.path.exists(res["answer_key_pdf"]))

    def tearDown(self):
        for p in [self.out_docx, self.out_pdf, self.out_key_pdf]:
            if os.path.exists(p):
                os.remove(p)
        if os.path.exists(self.out_pkg_dir):
            shutil.rmtree(self.out_pkg_dir)


if __name__ == "__main__":
    unittest.main()
