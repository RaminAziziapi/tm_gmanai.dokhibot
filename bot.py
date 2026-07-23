import os
import logging
from collections import defaultdict

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from google import genai


# ---------------- تنظیمات ----------------

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(name)


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL = "gemini-2.5-flash"


client = genai.Client(
    api_key=GEMINI_API_KEY
)


BOT_PERSONALITY = """
تو ربات «بذار من بگم» هستی.
یک دستیار باحال، با اعتماد به نفس و کمی شوخ هستی.
جواب‌ها کوتاه و طبیعی باشند.
مثل یک دوست صحبت کن، نه مثل مقاله.
اگر سوال مهم بود دقیق جواب بده.
"""


MAX_HISTORY = 10


user_history = defaultdict(list)


# ---------------- دستور شروع ----------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "سلام 👋\n"
        "من «بذار من بگم» هستم 😎\n"
        "سوالت رو بپرس تا جواب بدم."
    )


# ---------------- بررسی پاسخ در گروه ----------------


def can_reply(update):

    message = update.message

    if not message:
        return False


    # چت خصوصی
    if message.chat.type == "private":
        return True


    # اگر روی پیام ربات ریپلای شده
    if message.reply_to_message:
        return True


    # اگر اسم ربات منشن شده باشد
    if message.text and "@" in message.text:
        return True


    return False
# ---------------- ارتباط با Gemini ----------------


async def ask_gemini(user_id, text):

    user_history[user_id].append(
        {
            "role": "user",
            "content": text
        }
    )


    # فقط آخرین پیام‌ها نگه داشته شوند
    user_history[user_id] = user_history[user_id][-MAX_HISTORY:]


    prompt = BOT_PERSONALITY + "\n\n"


    for message in user_history[user_id]:
        prompt += (
            message["role"]
            + ": "
            + message["content"]
            + "\n"
        )


    try:

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )


        answer = response.text


        user_history[user_id].append(
            {
                "role": "assistant",
                "content": answer
            }
        )


        return answer


    except Exception as error:

        logger.error(error)

        return "یه مشکلی پیش اومد، دوباره امتحان کن."


# ---------------- دریافت پیام کاربران ----------------


async def message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return


    if not can_reply(update):
        return


    text = update.message.text

    if not text:
        return


    user_id = update.message.chat.id


    await update.message.chat.send_action(
        action="typing"
    )


    answer = await ask_gemini(
        user_id,
        text
    )


    await update.message.reply_text(
        answer
    )
# ---------------- اجرای ربات ----------------


def main():

    if not TELEGRAM_BOT_TOKEN:
        print("خطا: TELEGRAM_BOT_TOKEN تنظیم نشده")
        return


    if not GEMINI_API_KEY:
        print("خطا: GEMINI_API_KEY تنظیم نشده")
        return


    app = ApplicationBuilder() \
        .token(TELEGRAM_BOT_TOKEN) \
        .build()


    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler
        )
    )


    print("ربات روشن شد ✅")


    app.run_polling()



if name == "main":
    main()