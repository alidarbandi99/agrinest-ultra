# Agrinest Ultra — آزمایش‌خوان آفلاین آب و خاک

نمونه اولیه مستقل آزمایش‌خوان فارسی/انگلیسی، بدون ارتباط با Agrinestro. خواندن تصویر با Tesseract OCR محلی (در صورت نصب)، ورودی متن دستی، تشخیص عناصر و واحدها، پرچم‌گذاری ابهام، و بازبینی اجباری پیش از هر کاربرد تغذیه‌ای.

## اجرا

```bash
python app.py
```

سپس `http://127.0.0.1:8765` را باز کنید. در حالت بدون نصب Tesseract، ورودی متنی همچنان کار می‌کند. برای تصویر: Tesseract و بسته‌های زبان `fas` و `eng` را روی سیستم نصب کنید. هیچ تصویر یا عددی به سرور خارجی ارسال نمی‌شود.

## آزمون

```bash
python -m unittest discover -s tests -v
```

این نسخه هیچ توصیه کود صادر نمی‌کند و تشخیص تصویر بدون اجرای واقعی و سنجش با داده مرجع تأییدشده تلقی نمی‌شود. مقادیر نامشخص با صفر جایگزین نمی‌شوند. آزمایش خاک با مقدار mg/kg به mg/L آب تبدیل مستقیم نمی‌شود.


## ابزار خط فرمان جدید: eye.py

برای تصاویر و PDF، پس از نصب Tesseract با زبان فارسی و انگلیسی و بسته‌های Python:

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-fas tesseract-ocr-eng
python -m pip install -r requirements.txt
python eye.py /path/to/report.pdf --type water --output result.json
python eye.py /path/to/soil.jpg --type soil --output soil-result.json
```

برای بررسی منطق استخراج بدون OCR و بدون فایل آزمایش واقعی:

```bash
python eye.py examples/sample-water.txt --type water
python -m unittest discover -s tests -v
```

خروجی `eye.py` شامل مقدار، واحد به همان شکل خوانده‌شده، متن سطر اصلی، هشدار درباره داده نامطمئن و فهرست موارد نیازمند بازبینی است. تصاویر آزمایش واقعی را به مخزن عمومی push نکنید. OCR و تشخیص جدول/واحد هنوز با آزمایش‌های مرجع واقعی اعتبارسنجی نشده‌اند؛ تا بررسی انسانی، خروجی نباید مبنای تجویز کود باشد. ابزار CLI جدید مستقل از `app.py` و `engine.py` موجود است و یکپارچه‌سازی آن‌ها هنوز انجام نشده.
