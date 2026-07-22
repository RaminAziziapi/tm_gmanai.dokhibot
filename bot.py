"""
ربات تلگرامی که به Gemini (گوگل) وصل می‌شه و چت می‌کنه - کاملاً رایگان.

قبل از اجرا باید این‌ها رو تنظیم کنی:
1. TELEGRAM_BOT_TOKEN  -> توکنی که از BotFather گرفتی
2. GEMINI_API_KEY      -> کلید رایگان که از aistudio.google.com می‌گیری

این دو مقدار رو به صورت متغیر محیطی (Environment Variable) ست کن،
یا خیلی ساده داخل همین فایل جای‌گزین کن (پایین‌تر توضیح داده شده).
"""

import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from google import genai
from google.genai import types

# ---------------------------------------------------------------
# تنظیمات - این دو خط رو یا از Environment Variable می‌خونه
# یا می‌تونی مستقیم رشته‌ی توکن/کلید رو بین "" بذاری (برای تست سریع)
# ---------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "TOKEN-خودتو-اینجا-بذار")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "کلید-جمینای-خودتو-اینجا-بذار")
GEMINI_MODEL = "gemini-2.5-flash"  # مدل رایگان و سریع

# هر چند پیام آخر رو به عنوان حافظه‌ی مکالمه نگه داریم (به ازای هر کاربر)
MAX_HISTORY = 10

# شخصیت ربات - این متن به عنوان "system prompt" به کلود داده می‌شه
# و رفتار و لحنش رو مشخص می‌کنه. هر جور دوست داری می‌تونی عوضش کنی.
BOT_PERSONALITY = """
تو یه دستیار باحال و صمیمی هستی که تو یه گروه یا چت خصوصی تلگرام حرف می‌زنی.
لحنت خودمونی و دوستانه‌ست، نه رسمی و خشک. از طنز و شوخی مناسب استفاده کن،
جواب‌ها رو کوتاه و طبیعی بده (مثل یه آدم واقعی که تو چته، نه مثل یه مقاله).
می‌تونی از ایموجی به اندازه استفاده کنی ولی زیاده‌روی نکن.
اگه کسی سوال جدی پرسید جدی و دقیق جواب بده، ولی همیشه لحن گرم و انسانی‌تو حفظ کن.
"""

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

client = genai.Client(api_key=GEMINI_API_KEY)

# حافظه‌ی ساده‌ی مکالمه برای هر چت (خصوصی یا گروه) - در رم -> با ری‌استارت پاک می‌شه
user_histories: dict[int, list[dict]] = {}


def should_respond_in_group(update: Update, bot_username: str) -> bool:
    """تو گروه فقط وقتی جواب بده که ربات منشن شده باشه یا روی پیام خودش ریپلای شده باشه."""
    message = update.message

    # حالت ۱: کسی روی پیام قبلی ربات ریپلای زده
    if message.reply_to_messa