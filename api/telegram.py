from fastapi import FastAPI, Request, HTTPException, Response
import json
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, TypeHandler
from telegram.constants import ParseMode

# توکن بات و URL بازی
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GAME_URL = "https://MyNameisKaveh.github.io/awesome-telegram-game/"

# FastAPI app
app = FastAPI()

# --------- بخش مربوط به python-telegram-bot ---------
# به جای یک آبجکت application سراسری که حالت خودش رو بین فراخوانی‌ها از دست میده،
# ما یک تابع کمکی برای گرفتن یا ساختن application خواهیم داشت.
_telegram_app_instance = None

async def get_telegram_application():
    global _telegram_app_instance
    if _telegram_app_instance is None:
        if not BOT_TOKEN:
            print("CRITICAL: BOT_TOKEN environment variable not found!")
            raise RuntimeError("BOT_TOKEN not configured") # باعث خطا و عدم ادامه

        print("Initializing Telegram Application instance...")
        _telegram_app_instance = (
            Application.builder()
            .token(BOT_TOKEN)
            .read_timeout(7)  # زمان‌های کوتاه‌تر برای serverless
            .write_timeout(7)
            .connect_timeout(7)
            .pool_timeout(7) 
            .build()
        )

        # اضافه کردن هندلرها
        async def start_command(update: Update, context: _telegram_app_instance.context_type):
            await update.message.reply_text(
                "سلام! 👋 به بازی دوز حرفه‌ای خوش اومدی. برای شروع بازی دستور /play رو بزن."
            )

        async def play_command(update: Update, context: _telegram_app_instance.context_type):
            keyboard = [[
                InlineKeyboardButton(
                    "شروع بازی دوز 🎲", 
                    web_app=WebAppInfo(url=GAME_URL)
                )
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "برای شروع بازی روی دکمه زیر کلیک کن:",
                reply_markup=reply_markup
            )
        
        async def unknown_command(update: Update, context: _telegram_app_instance.context_type):
            await update.message.reply_text(
                "متوجه نشدم چی گفتی. از دستور /play برای شروع بازی استفاده کن."
            )

        _telegram_app_instance.add_handler(CommandHandler("start", start_command))
        _telegram_app_instance.add_handler(CommandHandler("play", play_command))
        _telegram_app_instance.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_command))
        
        # برای webhook، نیازی به initialize یا start_polling یا start_webhook نیست.
        # Application فقط برای پردازش آپدیت‌ها استفاده می‌شود.
        print("Telegram Application instance created and handlers registered.")
    return _telegram_app_instance

@app.post("/api/telegram")
async def webhook_handler(request: Request):
    try:
        application = await get_telegram_application() # دریافت یا ساخت application
        if not application: # اگر به خاطر نبود BOT_TOKEN ساخته نشده باشد
             raise HTTPException(status_code=500, detail="Bot Token not configured, application could not be initialized.")

        data = await request.json()
        update = Update.de_json(data, application.bot)
        
        # پردازش آپدیت
        await application.process_update(update)
            
        return Response(status_code=200, content="OK")

    except RuntimeError as e: # خطای مربوط به BOT_TOKEN
        print(f"RuntimeError in webhook_handler: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except json.JSONDecodeError:
        print("Error: Could not decode JSON from request body")
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    except Exception as e:
        print(f"Error processing update in webhook_handler: {e}")
        # در اینجا هم یک پاسخ 200 OK به تلگرام برمی‌گردانیم تا از تلاش مجدد جلوگیری شود
        # اما خطا را لاگ می‌کنیم.
        return Response(status_code=200, content=f"Error processed: {e}")

@app.get("/")
async def read_root():
    try:
        # فقط برای تست اینکه آیا BOT_TOKEN وجود دارد یا نه
        if not BOT_TOKEN:
             return {"message": "BOT_TOKEN not configured. Bot will not work."}
        # نمی‌توانیم get_me() را اینجا صدا بزنیم چون ممکن است application هنوز ساخته نشده باشد
        # و get_telegram_application یک تابع async است که در یک روت sync نمی‌توان await کرد
        # مگر اینکه read_root هم async باشد (که هست).
        application = await get_telegram_application()
        if application and application.bot:
            bot_info = await application.bot.get_me()
            return {"message": f"Bot @{bot_info.username} is configured via Vercel. Game is at {GAME_URL}"}
    except Exception as e:
        return {"message": f"Error checking bot status: {e}"}
    return {"message": "Vercel endpoint for Telegram bot. Send POST requests to /api/telegram"}
