from http.server import BaseHTTPRequestHandler
import json
import os
import telegram # pip install python-telegram-bot

# توکن بات را از متغیرهای محیطی Vercel بخوانید
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# URL بازی شما در GitHub Pages
GAME_URL = "https://MyNameisKaveh.github.io/awesome-telegram-game/" # URL صحیح بازی خودتان را اینجا قرار دهید

bot = telegram.Bot(token=BOT_TOKEN)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update_data = json.loads(post_data.decode('utf-8'))
            
            update = telegram.Update.de_json(update_data, bot)

            if update.message and update.message.text:
                chat_id = update.message.chat_id
                text = update.message.text

                if text == "/start":
                    bot.send_message(
                        chat_id=chat_id, 
                        text="سلام! 👋 به بازی دوز حرفه‌ای خوش اومدی. برای شروع بازی دستور /play رو بزن."
                    )
                elif text == "/play":
                    keyboard = [[
                        telegram.InlineKeyboardButton(
                            "شروع بازی دوز 🎲", 
                            web_app=telegram.WebAppInfo(url=GAME_URL) # فعلا مستقیم به URL وب‌اپ لینک میدیم
                        )
                    ]]
                    reply_markup = telegram.InlineKeyboardMarkup(keyboard)
                    bot.send_message(
                        chat_id=chat_id, 
                        text="برای شروع بازی روی دکمه زیر کلیک کن:",
                        reply_markup=reply_markup
                    )
                else:
                    bot.send_message(
                        chat_id=chat_id,
                        text="متوجه نشدم چی گفتی. از دستور /play برای شروع بازی استفاده کن."
                    )
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")

        except Exception as e:
            print(f"Error: {e}") # برای دیباگ در لاگ‌های Vercel
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Error processing request")
        return
