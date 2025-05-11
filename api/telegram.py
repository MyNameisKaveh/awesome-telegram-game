from fastapi import FastAPI, Request, HTTPException, Response
import json
import os
import asyncio # اضافه کردن asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, TypeHandler
from telegram.constants import ParseMode

# توکن بات را از متغیرهای محیطی Vercel بخوانید
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# URL بازی شما در GitHub Pages
GAME_URL = "https://MyNameisKaveh.github.io/awesome-telegram-game/" # URL صحیح بازی خودتان

# یک نمونه از FastAPI app بسازید
app = FastAPI()

# --------- بخش مربوط به python-telegram-bot ---------
application = None

async def setup_telegram_app():
    global application
    if not BOT_TOKEN:
        print("CRITICAL: BOT_TOKEN environment variable not found!")
        # در این حالت، application ساخته نخواهد شد و بات کار نمی‌کند
        return

    # به جای ساخت مستقیم Bot، از Application استفاده می‌کنیم
    # این به مدیریت بهتر context و event loop کمک می‌کند
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .read_timeout(30)  # افزایش زمان خواندن
        .write_timeout(30) # افزایش زمان نوشتن
        .connect_timeout(30) # افزایش زمان اتصال
        .pool_timeout(30) # افزایش زمان انتظار برای کانکشن از پول
        .build()
    )

    # اضافه کردن هندلرها به application
    # دستور /start
    async def start_command(update: Update, context: application.context_type):
        await update.message.reply_text(
            "سلام! 👋 به بازی دوز حرفه‌ای خوش اومدی. برای شروع بازی دستور /play رو بزن."
        )

    # دستور /play
    async def play_command(update: Update, context: application.context_type):
        keyboard = [[
            telegram.InlineKeyboardButton(
                "شروع بازی دوز 🎲", 
                web_app=telegram.WebAppInfo(url=GAME_URL)
            )
        ]]
        reply_markup = telegram.InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "برای شروع بازی روی دکمه زیر کلیک کن:",
            reply_markup=reply_markup
        )
    
    # هندلر برای پیام‌های ناشناس
    async def unknown_command(update: Update, context: application.context_type):
        await update.message.reply_text(
            "متوجه نشدم چی گفتی. از دستور /play برای شروع بازی استفاده کن."
        )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("play", play_command))
    # این هندلر باید بعد از CommandHandlerها بیاد تا پیام‌های ناشناس رو بگیره
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_command))

    # (اختیاری) برای اینکه مطمئن شویم application یکبار initialize شده
    # این کار برای محیط serverless که تابع ممکن است چندین بار فراخوانی شود، مهم است
    # await application.initialize() # این کار را در رویداد startup FastAPI انجام می‌دهیم

# رویداد startup برای FastAPI تا application تلگرام را یکبار initialize کند
@app.on_event("startup")
async def startup_event():
    print("FastAPI startup: Initializing Telegram Application...")
    await setup_telegram_app()
    if application and application.updater: # اگر از Updater استفاده می‌کردیم (که اینجا نمی‌کنیم)
        # برای Webhook، نیازی به application.run_polling() یا application.start() نیست
        print("Telegram Application initialized with webhook setup (manual).")
    elif application:
        print("Telegram Application Bot instance created.")
    else:
        print("Failed to initialize Telegram Application.")


@app.post("/api/telegram") # مسیر وب‌هوک ما
async def webhook_handler(request: Request):
    if not application:
        print("Error: Telegram application not initialized!")
        raise HTTPException(status_code=500, detail="Bot not initialized properly. Check logs.")
            
    try:
        # اجرای پراسس آپدیت در یک تسک جداگانه asyncio
        # این به FastAPI اجازه می‌دهد سریعاً پاسخ 200 را برگرداند
        # و پردازش آپدیت در پس‌زمینه انجام شود.
        # این کار برای جلوگیری از timeout تلگرام مفید است.
        
        data = await request.json()
        update = Update.de_json(data, application.bot)
        
        # به جای application.process_update(update) که ممکن است event loop را مسدود کند،
        # سعی می‌کنیم آپدیت را به صورت غیرمستقیم مدیریت کنیم یا مطمئن شویم که
        # هندلرهای ما سریع هستند.
        # برای سادگی فعلاً مستقیم پراسس می‌کنیم، اما در نظر داشته باشید.
        
        # یک تسک برای پردازش آپدیت ایجاد می‌کنیم
        # loop = asyncio.get_event_loop()
        # loop.create_task(application.process_update(update))

        # یا به صورت ساده‌تر و مستقیم‌تر برای شروع:
        await application.process_update(update)
            
        return Response(status_code=200, content="OK") # پاسخ ساده 200 OK

    except json.JSONDecodeError:
        print("Error: Could not decode JSON from request body")
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    except Exception as e:
        print(f"Error processing update in webhook_handler: {e}")
        # به تلگرام یک پاسخ خطا برنگردانید مگر اینکه بخواهید دوباره تلاش کند
        return Response(status_code=200, content="Error processed, no retry.") # یا 500 اگر می‌خواهید مشکل را در تلگرام هم ببینید

# (اختیاری) یک روت برای ریشه پروژه
@app.get("/")
async def read_root():
    if application:
        bot_info = await application.bot.get_me()
        return {"message": f"Bot @{bot_info.username} is configured. Game is at {GAME_URL}"}
    return {"message": "Bot not configured (BOT_TOKEN missing or other issue)."}
