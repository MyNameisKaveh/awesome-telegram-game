from fastapi import FastAPI, Request, HTTPException
import json
import os
import telegram # python-telegram-bot

# توکن بات را از متغیرهای محیطی Vercel بخوانید
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# URL بازی شما در GitHub Pages
GAME_URL = "https://MyNameisKaveh.github.io/awesome-telegram-game/" # URL صحیح بازی خودتان

# یک نمونه از FastAPI app بسازید
# Vercel به طور خودکار متغیر 'app' رو به عنوان نقطه ورود ASGI پیدا می‌کنه
app = FastAPI()

# یک نمونه از Bot بسازید
# مهم: مطمئن شوید که BOT_TOKEN به درستی از متغیرهای محیطی خوانده شده
if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN environment variable not found!")
    # در محیط پروداکشن، این باید باعث خطا در بیلد یا اجرا بشه
    # برای جلوگیری از خطای NoneType، یک توکن موقت می‌گذاریم یا برنامه را متوقف می‌کنیم
    # اما بهترین کار این است که مطمئن شویم متغیر محیطی همیشه هست.
    bot = None # یا raise Exception("BOT_TOKEN not found")
else:
    bot = telegram.Bot(token=BOT_TOKEN)


@app.post("/api/telegram") # مسیر وب‌هوک ما، فقط متد POST رو قبول می‌کنه
async def webhook_handler(request: Request):
    if not bot:
        raise HTTPException(status_code=500, detail="Bot not initialized. Check BOT_TOKEN.")
        
    try:
        body = await request.json()
        update = telegram.Update.de_json(body, bot)
        
        if update.message and update.message.text:
            chat_id = update.message.chat_id
            text = update.message.text

            if text == "/start":
                await bot.send_message(
                    chat_id=chat_id, 
                    text="سلام! 👋 به بازی دوز حرفه‌ای خوش اومدی. برای شروع بازی دستور /play رو بزن."
                )
            elif text == "/play":
                keyboard = [[
                    telegram.InlineKeyboardButton(
                        "شروع بازی دوز 🎲", 
                        web_app=telegram.WebAppInfo(url=GAME_URL)
                    )
                ]]
                reply_markup = telegram.InlineKeyboardMarkup(keyboard)
                await bot.send_message(
                    chat_id=chat_id, 
                    text="برای شروع بازی روی دکمه زیر کلیک کن:",
                    reply_markup=reply_markup
                )
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text="متوجه نشدم چی گفتی. از دستور /play برای شروع بازی استفاده کن."
                )
        
        return {"status": "ok"}

    except json.JSONDecodeError:
        print("Error: Could not decode JSON from request body")
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    except Exception as e:
        print(f"Error processing update: {e}") # برای دیباگ در لاگ‌های Vercel
        # به تلگرام یک پاسخ موفقیت‌آمیز برگردانید تا از ارسال مجدد جلوگیری شود،
        # مگر اینکه بخواهید تلگرام دوباره تلاش کند (که معمولاً برای خطاهای داخلی خوب نیست).
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

# (اختیاری) یک روت برای ریشه پروژه که بازی را نمایش می‌دهد
# این تنها زمانی کار می‌کند که فایل‌های بازی شما در Vercel هم دیپلوی شده باشند
# و نه فقط در GitHub Pages. فعلاً ما از GitHub Pages برای بازی استفاده می‌کنیم.
# @app.get("/")
# async def read_root():
#     return {"message": "Bot is running. Game is hosted on GitHub Pages."}
