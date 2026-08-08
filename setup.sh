#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# راه‌اندازی برنامه روی لینوکس / مک
# اجرا:  bash setup.sh
# ---------------------------------------------------------------------------
set -e

cd "$(dirname "$0")"

PY=${PYTHON:-python3}

echo "==> ساخت محیط مجازی"
if [ ! -d "venv" ]; then
  "$PY" -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate

echo "==> نصب جنگو"
pip install --upgrade pip >/dev/null
pip install -r requirements.txt

echo "==> ساخت جداول دیتابیس"
python manage.py makemigrations ledger
python manage.py migrate

echo "==> ساخت حساب مدیر و دسته‌بندی‌های پیش‌فرض"
read -r -p "نام کاربری مدیر (پیش‌فرض admin): " USERNAME
USERNAME=${USERNAME:-admin}
read -r -s -p "رمز عبور مدیر (حداقل ۶ نویسه): " PASSWORD
echo
read -r -p "نام و نام خانوادگی: " FULLNAME

python manage.py init_app --username "$USERNAME" --password "$PASSWORD" --name "$FULLNAME"

cat <<'MSG'

========================================================
 آماده است! برای اجرای برنامه:

   source venv/bin/activate
   python manage.py runserver 0.0.0.0:8000

 روی همین کامپیوتر:      http://127.0.0.1:8000
 از گوشی در همان وای‌فای: http://IP-کامپیوتر:8000
========================================================
MSG
