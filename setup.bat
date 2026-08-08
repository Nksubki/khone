@echo off
REM ---------------------------------------------------------------------------
REM  راه اندازی برنامه روی ویندوز — روی این فایل دوبار کلیک کنید
REM ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0"

echo ==^> ساخت محیط مجازی
if not exist venv (
  python -m venv venv
)
call venv\Scripts\activate.bat

echo ==^> نصب جنگو
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo ==^> ساخت جداول دیتابیس
python manage.py makemigrations ledger
python manage.py migrate
if errorlevel 1 goto :error

echo.
set /p USERNAME="نام کاربری مدیر (پیش فرض admin): "
if "%USERNAME%"=="" set USERNAME=admin
set /p PASSWORD="رمز عبور مدیر (حداقل 6 نویسه): "
set /p FULLNAME="نام و نام خانوادگی: "

python manage.py init_app --username "%USERNAME%" --password "%PASSWORD%" --name "%FULLNAME%"
if errorlevel 1 goto :error

echo.
echo ========================================================
echo  آماده است! برای اجرا:
echo     venv\Scripts\activate
echo     python manage.py runserver 0.0.0.0:8000
echo  سپس در مرورگر: http://127.0.0.1:8000
echo ========================================================
echo.
pause
exit /b 0

:error
echo.
echo خطا رخ داد. متن خطا را بررسی کنید.
pause
exit /b 1
