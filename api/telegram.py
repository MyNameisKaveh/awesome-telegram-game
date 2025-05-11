from fastapi import FastAPI, Request, HTTPException, Response
import json
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes # ContextTypes اضافه شد

# توکن بات و URL بازی
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GAME_URL = "https://MyNameisKaveh.github.io/awesome-telegram-game/"

app = FastAPI()

_telegram_app_instance = None

async def get_telegram_application():
    global _telegram_app_instance
    if _telegram_app_instance is None:
        print("Attempting to initialize Telegram Application instance...")
        if not BOT_TOKEN:
            print("CRITICAL: BOT_TOKEN environment variable not found during get_telegram_application!")
            return None 

        print(f"BOT_TOKEN found, starts with: {BOT_TOKEN[:5]}... and ends with: {BOT_TOKEN[-5:]}")
        
        # استفاده از Application.builder()
        builder = Application.builder().token(BOT_TOKEN)
        builder.read_timeout(7).write_timeout(7).connect_timeout(7).pool_timeout(7)
        
        _telegram_app_instance = builder.build()

        # >>>>>>>> تغییر مهم: فراخوانی initialize <<<<<<<<
        await _telegram_app_instance.initialize() 
        print("Telegram Application initialized.")

        # تعریف توابع هندلر
        # >>>>>>>> تغییر مهم: استفاده از ContextTypes.DEFAULT_TYPE برای context <<<<<<<<
        async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            print(f"Executing start_command for chat_id: {update.message.chat_id}")
            await update.message.reply_text(
                "سلام! 👋 به بازی دوز حرفه‌ای خوش اومدی. برای شروع بازی دستور /play رو بزن."
            )

        async def play_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            print(f"Executing play_command for chat_id: {update.message.chat_id}")
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
        
        async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            print(f"Executing unknown_command for chat_id: {update.message.chat_id}")
            await update.message.reply_text(
                "متوجه نشدم چی گفتی. از دستور /play برای شروع بازی استفاده کن."
            )

        _telegram_app_instance.add_handler(CommandHandler("start", start_command))
        _telegram_app_instance.add_handler(CommandHandler("play", play_command))
        _telegram_app_instance.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_command))
        
        print("Telegram Application instance created, initialized, and handlers registered.")
    else:
        print("Reusing existing Telegram Application instance.")
    return _telegram_app_instance


@app.post("/api/telegram")
async def webhook_handler(request: Request):
    print("Webhook handler called.")
    current_app = await get_telegram_application()

    if not current_app:
        print("Error: Telegram application could not be initialized in webhook_handler (likely BOT_TOKEN issue).")
        raise HTTPException(status_code=500, detail="Bot (application) could not be initialized. Check server logs for BOT_TOKEN issues.")
            
    try:
        data = await request.json()
        # print(f"Received update: {json.dumps(data, indent=2)}") 

        update = Update.de_json(data, current_app.bot)
        
        print("Processing update with Telegram Application...")
        await current_app.process_update(update)
        print("Update processed successfully.")
            
        return Response(status_code=200, content="OK")

    except json.JSONDecodeError:
        print("Error: Could not decode JSON from request body")
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    except Exception as e:
        print(f"Error during update processing in webhook_handler: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error during processing: {e}")


@app.get("/")
async def read_root():
    print("Root path handler called.")
    try:
        current_app_for_root = await get_telegram_application()
        if not current_app_for_root:
            return {"message": "BOT_TOKEN not configured or other init error. Bot will not work."}
        
        if hasattr(current_app_for_root, 'bot') and current_app_for_root.bot is not None:
            bot_info = await current_app_for_root.bot.get_me()
            return {"message": f"Bot @{bot_info.username} is configured via Vercel. Game is at {GAME_URL}"}
        else:
            return {"message": "Bot object not found within application instance, likely BOT_TOKEN issue or init error."}
            
    except Exception as e:
        print(f"Error in read_root: {e}")
        return {"message": f"Error checking bot status: {e}"}
