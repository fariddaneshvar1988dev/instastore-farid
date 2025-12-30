# استفاده از نسخه سبک پایتون برای پروداکشن
FROM python:3.10-slim

# تنظیم متغیرهای محیطی برای بهینه‌سازی پایتون در داکر
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ساخت پوشه کاری داخل کانتینر
WORKDIR /app

# نصب پیش‌نیازهای سیستمی (برای پستگرس و کامپایلرها لازم میشه)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# کپی کردن فایل نیازمندی‌ها و نصب آن‌ها
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# کپی کردن کل پروژه به داخل کانتینر
COPY . /app/

# دستور پیش‌فرض برای اجرای سرور روی پورت 8000
CMD ["gunicorn", "instastore.wsgi:application", "--bind", "0.0.0.0:8000"]