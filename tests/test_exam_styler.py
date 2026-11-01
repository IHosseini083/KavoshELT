import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from exam_styler import generate_exam_docx, generate_exam_pdf

class TestExamStyler(unittest.TestCase):
    def setUp(self):
        self.sample_exam_md = "/home/ubuntu/آزمون_شنیداری_زبان_انگلیسی_پایه_دهم_نوبت_اول.md"
        self.out_docx = "/tmp/test_exam.docx"
        self.out_pdf = "/tmp/test_exam.pdf"

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
        self.assertGreater(os.path.getsize(self.out_pdf), 2000)

    def tearDown(self):
        if os.path.exists(self.out_docx):
            os.remove(self.out_docx)
        if os.path.exists(self.out_pdf):
            os.remove(self.out_pdf)

if __name__ == "__main__":
    unittest.main()
