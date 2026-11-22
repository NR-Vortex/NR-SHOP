# NR SHOP · فروشگاه تلگرامی و پنل نمایندگی

[![Release](https://img.shields.io/github/v/release/NR-Vortex/NR-SHOP)](https://github.com/NR-Vortex/NR-SHOP/releases/latest)
[![Docker build](https://github.com/NR-Vortex/NR-SHOP/actions/workflows/build.yml/badge.svg)](https://github.com/NR-Vortex/NR-SHOP/actions/workflows/build.yml)
[![Telegram](https://img.shields.io/badge/Platform-Telegram-229ED9)](https://core.telegram.org/bots/webapps)

[نصاب مستقیم](https://raw.githubusercontent.com/NR-Vortex/NR-SHOP/main/install.sh) · [انتشارها](https://github.com/NR-Vortex/NR-SHOP/releases) · [پیشنهاد قابلیت و گزارش اشکال](https://github.com/NR-Vortex/NR-SHOP/issues/new)

[English documentation](README.en.md)

NR SHOP یک فروشگاه خودمیزبان تلگرام برای فروش اشتراک VPN و محصولات دیجیتال است. مدیر سرور مرکزی، فروش، رسیدها و نماینده‌ها را از ربات و مینی‌اپ مدیریت می‌کند.

## امکانات

- فروشگاه VPN و AI، سبد سفارش، کد تخفیف و بررسی رسید کارت‌به‌کارت
- پنل نمایندگی SaaS با خرید حجم، سهمیه مستقل و ساخت کانفیگ روی 3x-ui مرکزی
- ربات فروش اختیاری هر نماینده با مشتریان مستقل، بسته و قیمت اختصاصی و بررسی دستی رسید
- مینی‌اپ فارسی و راست‌به‌چپ برای مدیر و نماینده، تنظیم رنگ دکمه‌ها و پیش‌نمایش تم
- کیف پول، گزارش فروش، پشتیبانی، عضویت اجباری و بکاپ PostgreSQL و تنظیمات

## نصب روی لینوکس

روی سرور به Docker Engine، افزونه Docker Compose، curl، OpenSSL و Python 3 نیاز داری. توکن را از BotFather بگیر و شناسه عددی مدیر را آماده کن.

```bash
curl -fLo nr-shop-install.sh https://raw.githubusercontent.com/NR-Vortex/NR-SHOP/main/install.sh
bash nr-shop-install.sh
```

نصاب توکن را بررسی می‌کند و لینک همان ربات را نشان می‌دهد. در ربات Start بزن و چت‌آیدی خصوصی عددی‌ات را وارد کن تا همان حساب مدیر نصب شود. نصاب سپس دامنه اختیاری مینی‌اپ را می‌پرسد، کلیدها را محلی می‌سازد و مهاجرت دیتابیس را اجرا می‌کند. اگر دامنه را خالی بگذاری، می‌توانی ربات را بدون مینی‌اپ عمومی اجرا کنی.

| پورت | کاربرد |
| --- | --- |
| TCP 80 و 443 | ورودی وب برای Caddy و HTTPS مینی‌اپ. رکورد DNS دامنه باید به سرور اشاره کند. |
| TCP 8080 | API مینی‌اپ، داخلی در شبکه Docker |
| TCP 5432 | PostgreSQL، داخلی در شبکه Docker |
| خروجی TCP 443 | اتصال ربات به Telegram Bot API. ارتباط با 3x-ui از پورت آدرس پنل استفاده می‌کند. |

بعد از نصب، در ربات `/admin` را بزن. از بخش VPN پنل 3x-ui و ورودی را اضافه کن و در تنظیمات نمایندگی، آدرس اشتراک و قیمت هر گیگ را ثبت کن. برای کارت‌به‌کارت فروشگاه اصلی، مقادیر `PAYMENT_BANK_NAME`، `PAYMENT_CARD_NUMBER` و `PAYMENT_CARDHOLDER` را در فایل محلی `.env` بگذار و سرویس‌ها را دوباره بالا بیاور.

```bash
cd nr-shop
docker compose -f compose.production.yaml logs -f bot miniapp
# اگر دامنه تنظیم کردی
docker compose -f compose.production.yaml --profile https up -d
```

از فایل `.env` و بکاپ‌ها خصوصی نگهداری کن. بازیابی توکن‌های رمزگذاری‌شده و اطلاعات اتصال پنل به همان کلیدهای اولیه نیاز دارد.

## به‌روزرسانی از تلگرام

ربات مدیران همان نصب را از نسخهٔ پایدار جدید باخبر می‌کند. «جزئیات نسخه در GitHub» تغییرات را باز می‌کند. «نصب روی همین سرور» پس از تأیید مدیر، درخواست را به سرویس محلی می‌سپارد. نسخه و نتیجهٔ نصب را از منوی «به‌روزرسانی» ببین.

اگر سرویس هنگام نصب فعال نشده، از داخل پوشهٔ نصب اجرا کن:

```bash
bash scripts/enable-updates.sh
```

سرویس به حساب غیر root با دسترسی Docker و نشست سالم `systemd --user` نیاز دارد. برای فعال ماندن تایمر بعد از خروج از SSH، مدیر سرور می‌تواند `loginctl enable-linger` را برای حساب نصب فعال کند. نصب‌های قدیمی یک بار باید دستی به نسخهٔ دارای این اسکریپت ارتقا پیدا کنند؛ فایل `.env` و حجم‌های Docker را حفظ کن.

به‌روزرسان آخرین انتشار پایدار مخزن رسمی را بررسی می‌کند، از PostgreSQL و تنظیمات در `.update-backups` بکاپ می‌گیرد و قبل از راه‌اندازی دوباره، مهاجرت را اجرا می‌کند.

## مشارکت و حمایت

با Star، معرفی پروژه، گزارش اشکال یا Pull Request از توسعه حمایت کن. در گزارش، نسخه و مراحل بازتولید را بنویس و اطلاعات مشتری و کلیدها را حذف کن.
