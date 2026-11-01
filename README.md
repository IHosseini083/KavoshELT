# پایگاه دانش و اعتبارسنج برنامه درسی زبان انگلیسی (پایه‌های ۷ تا ۱۲)
# Iranian Secondary English Curriculum Knowledge Base & Exam Validator

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-25%20passed-brightgreen.svg)]()
[![Zero Dependencies](https://img.shields.io/badge/dependencies-stdlib%20only-success.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

یک پلتفرم کامل، بدون وابستگی خارجی (Standard Library Only) و متن‌باز برای **اعتبارسنجی سطح کتاب‌های درسی**، **قفل واژگان و گرامر مجاز**، و **طراحی هوشمند آزمون‌های کتبی و شنیداری (Listening)** بر اساس سرفصل‌های رسمی وزارت آموزش و پرورش ایران:
* **دوره اول متوسطه (راهنمایی):** کتاب‌های *Prospect 1, 2, 3* (پایه‌های هفتم، هشتم و نهم)
* **دوره دوم متوسطه (دبیرستان):** کتاب‌های *Vision 1, 2, 3* (پایه‌های دهم، یازدهم و دوازدهم)

---

## 🌟 ویژگی‌های کلیدی (Key Features)

1. **پوشش کامل ۶ پایه و ۳۱ درس مصوب (31 Official Lessons):**
   * پایگاه داده ساختاریافته SQLite با بیش از ۱,۰۵۰ واژه مصوب، الگوهای گرامری مجاز و خطوط قرمز (گرامرهای ممنوعه در هر پایه).
   * موتور جستجوی تمام‌متن FTS5 روی تمامی ریدینگ‌ها و مکالمات کتب درسی.
2. **اعتبارسنجی دقیق و بدون خطا (Zero Out-of-Syllabus Guarantee):**
   * ریشه‌یابی و تطبیق هوشمند صرفی واژگان (Inflection & Lemmatization) برای پسوندها (`-s`, `-ed`, `-ing`, `-er`, `-est`, `-ly`) و افعال بی‌قاعده.
   * شناسایی ساختارهای دستوری تدریس‌نشده (مثلاً ممنوعیت زمان حال کامل در پایه دهم یا مجهول در پایه‌های ۷ تا ۱۱).
3. **پیشنهاددهنده جایگزین‌های مجاز (In-Syllabus Synonym Advisor):**
   * هنگام تشخیص کلمه خارج از کتاب، سیستم فوراً نشان می‌دهد آن کلمه در چه پایه‌ای تدریس می‌شود و **کلمات معادل از پایه‌های قبل** را پیشنهاد می‌دهد (مثلاً پیشنهاد `doctor` به جای `physician` برای پایه هفتم).
4. **تولید خودکار بلوپرینت آزمون و صوت هوش مصنوعی (AI TTS Ready):**
   * خروجی مستقیم ساختار آزمون بر اساس بودجه‌بندی و بارم‌بندی رسمی دفتر تألیف.
   * فرمت آماده برای مدل‌های صوتی نظیر **Gemini 3.8 Flash TTS** (با گویندگان Fola و Rami) و **ElevenLabs**.

---

## 📊 جدول پیشرفت آموزشی ۶ پایه (Curriculum Progression)

| پایه | کتاب | تعداد درس | گرامرهای مجاز (In-Scope) | گرامرهای خط قرمز (Out-of-Scope) |
|:---:|:---:|:---:|:---|:---|
| **هفتم** | Prospect 1 | ۸ درس | افعال To Be، ضمایر ملکی، احوالپرسی، حال استمراری | زمان گذشته، آینده، افعال کمکی، مجهول |
| **هشتم** | Prospect 2 | ۷ درس | توانایی با Can، زمان حال ساده با Do/Does، بیماری‌ها | زمان گذشته، آینده، حال کامل، مجهول |
| **نهم** | Prospect 3 | ۶ درس | زمان گذشته ساده (با قاعده و بی‌قاعده)، گذشته افعال To Be | آینده با Will، حال کامل، مجهول، شرطی‌ها |
| **دهم** | Vision 1 | ۴ درس | آینده ساده با Will و Be going to، صفت‌های تفضیلی/عالی، گذشته استمراری | حال کامل (Present Perfect)، مجهول، شرطی ۲ |
| **یازدهم** | Vision 2 | ۳ درس | حال کامل (have/has + p.p)، اسم مصدر و مصدر با to، شرطی نوع اول | مجهول (Passive Voice)، شرطی نوع دوم |
| **دوازدهم** | Vision 3 | ۳ درس | مجهول (در تمام زمان‌ها)، جملات موصولی (who/which)، گذشته کامل، شرطی ۲ | — (کل گرامر متوسطه) |

---

## 🚀 راهنمای استفاده سریع (CLI Usage)

تمامی دستورات بدون نیاز به نصب پکیج و با پایتون استاندارد اجرا می‌شوند:

### ۱. آمار کلی پایگاه دانش
```bash
python3 curriculum_kb.py stats
```

### ۲. استخراج محدودیت‌های یک درس برای پرامپت هوش مصنوعی
```bash
# دریافت واژگان، گرامرها و بارم‌بندی نوبت اول دهم (دروس ۱ و ۲):
python3 curriculum_kb.py context --grade 10 --lessons 1,2
```

### ۳. اعتبارسنجی متن آزمون (بررسی خارج از کتاب نبودن)
```bash
python3 curriculum_kb.py validate --grade 10 --max-lesson 2 --text "The heart pumps blood through the body."
```

### ۴. تطبیق متن و دریافت پیشنهادات جایگزین (Adapt & Advise)
```bash
python3 curriculum_kb.py adapt --grade 7 --max-lesson 8 --text "The physician helped the patient."
```
*خروجی نشان می‌دهد که `physician` در پایه دهم درس ۳ تدریس می‌شود و معادل مجاز آن در پایه هفتم کلمه `doctor` است.*

### ۵. جستجوی متون رسمی کتاب درسی (FTS5 Search)
```bash
python3 curriculum_kb.py search --query "cheetah"
```

### ۶. ممیزی خودسازگاری دیتابیس (Curriculum Self-Audit)
```bash
python3 curriculum_kb.py audit
```

### ۷. دریافت بلوپرینت آزمون و مشخصات صوت هوش مصنوعی
```bash
python3 curriculum_kb.py blueprint --grade 9 --term 1 --exam-type Listening
```

---

## 🧪 تست‌های واحد (Test Suite)

برای اجرای تمامی ۲۵ تست واحد TDD:
```bash
python3 -m unittest discover -s tests
```

---

## 📁 ساختار مخزن (Repository Structure)

```text
vision_kb/
├── curriculum_kb.py       # ابزار جامع خط فرمان (CLI)
├── schema.py              # ساختار پایگاه داده SQLite و جدول مجازی FTS5
├── seed_all_grades.py     # اسکریپت ساخت پایگاه داده از روی JSONها
├── validator.py           # موتور اعتبارسنج واژگان و گرامر
├── advisor.py             # پیشنهاددهنده مترادف‌های داخل سیلابس
├── auditor.py             # ممیز خودکار سازگاری متون کتاب
├── datasets/              # دیتای خام و نسخه شده هر ۶ پایه
│   ├── grade7_prospect1.json
│   ├── grade8_prospect2.json
│   ├── grade9_prospect3.json
│   ├── grade10_vision1.json
│   ├── grade11_vision2.json
│   └── grade12_vision3.json
├── docs/                  # مستندات تکمیلی معماری و راهنمای دبیران
│   ├── ARCHITECTURE.md
│   ├── CURRICULUM_MAP.md
│   └── TEACHER_GUIDE.md
├── scripts/               # اسکریپت‌های اعتبارسنجی و دانلود PDF
│   └── fetch_and_verify_pdfs.py
└── tests/                 # ۲۵ تست واحد استاندارد
```

---

## 📄 مجوز (License)
این پروژه تحت مجوز **MIT** منتشر شده است. استفاده برای اهداف آموزشی، مدارس و دبیران زبان انگلیسی کاملاً آزاد و رایگان است.
