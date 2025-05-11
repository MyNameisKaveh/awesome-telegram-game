from fastapi import FastAPI, Request, HTTPException, Depends
from pydantic import BaseModel, Field # برای اعتبارسنجی داده‌های ورودی
import os
from vercel_kv import KV # کتابخانه Vercel برای KV store
import hashlib # برای هش کردن initData
import hmac
from urllib.parse import parse_qsl, unquote
from typing import Optional

# FastAPI app (Vercel به طور خودکار 'app' رو پیدا می‌کنه اگر فایل در پوشه api باشه)
app = FastAPI()

# مدل داده برای ورودی تابع submit_score
class ScoreData(BaseModel):
    score: int
    game_type: Optional[str] = "tictactoe_default" # نوع بازی، برای آینده
    # initData رو برای اعتبارسنجی می‌گیریم
    # این رو از window.Telegram.WebApp.initData در فرانت‌اند می‌فرستیم
    initData: str = Field(..., alias="telegramInitData") 

# متغیرهای محیطی KV store که توسط Vercel تنظیم شدن
# کتابخانه vercel_kv به طور خودکار این‌ها رو می‌خونه اگر با پیشوند KV_ باشن
# KV_URL (یا UPSTASH_REDIS_REST_URL)
# KV_REST_API_TOKEN (یا UPSTASH_REDIS_REST_TOKEN)
# KV_REST_API_READ_ONLY_TOKEN (استفاده نمیشه برای نوشتن)

# توکن بات برای اعتبارسنجی initData (باید از متغیرهای محیطی خوانده شود)
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# ---------- تابع برای اعتبارسنجی initData ----------
# این تابع خیلی مهمه برای جلوگیری از تقلب
def validate_init_data(init_data_str: str, bot_token: str) -> Optional[dict]:
    """
    Validates the initData string from Telegram Web App.
    Returns the user data dict if valid, None otherwise.
    """
    if not bot_token:
        print("Error: BOT_TOKEN not available for initData validation.")
        return None

    # initData یک رشته query string هست. اون رو به دیکشنری تبدیل می‌کنیم.
    # ترتیب کلیدها برای هش کردن مهمه.
    # ابتدا hash رو جدا می‌کنیم
    try:
        parsed_data = dict(parse_qsl(init_data_str))
    except Exception as e:
        print(f"Error parsing initData string: {e}")
        return None

    if "hash" not in parsed_data:
        print("Error: 'hash' not found in initData.")
        return None
    
    received_hash = parsed_data.pop("hash")

    # رشته data-check-string رو می‌سازیم. کلیدها باید به ترتیب الفبا مرتب بشن.
    data_check_string_parts = []
    for key, value in sorted(parsed_data.items()):
        data_check_string_parts.append(f"{key}={value}")
    data_check_string = "\n".join(data_check_string_parts)

    # هش رو با استفاده از توکن بات محاسبه می‌کنیم
    secret_key = hmac.new("WebAppData".encode(), bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if calculated_hash == received_hash:
        print("initData validation successful.")
        try:
            # user_data معمولاً به صورت JSON در فیلد 'user' قرار داره
            if 'user' in parsed_data:
                user_info = json.loads(parsed_data['user'])
                return user_info # یا کل parsed_data اگر نیاز به اطلاعات دیگه هم دارید
            else:
                print("Warning: 'user' field not found in parsed_data after validation.")
                return None # یا یک دیکشنری خالی اگر این حالت رو می‌پذیرید
        except json.JSONDecodeError:
            print("Error: Could not decode 'user' field from initData.")
            return None
    else:
        print(f"initData validation failed. Calculated: {calculated_hash}, Received: {received_hash}")
        return None

# ---------- API Endpoint برای ذخیره امتیاز ----------
@app.post("/api/submit_score")
async def submit_score(score_input: ScoreData, request: Request):
    print(f"Received score submission: Score={score_input.score}, GameType={score_input.game_type}")
    
    # ۱. اعتبارسنجی initData
    user_data = validate_init_data(score_input.initData, BOT_TOKEN)
    if not user_data or 'id' not in user_data:
        print("Score submission rejected: Invalid or missing user data from initData.")
        raise HTTPException(status_code=403, detail="Invalid user authentication (initData).")

    user_id = user_data['id']
    username = user_data.get('username', f"user_{user_id}") # اگر یوزرنیم نباشه، یک پیش‌فرض می‌سازیم
    first_name = user_data.get('first_name', "Player")

    print(f"Score submitted by User ID: {user_id}, Username: {username}, First Name: {first_name}")

    # ۲. ذخیره امتیاز در KV Store (Redis)
    # ما می‌خوایم از Sorted Set برای لیدربورد استفاده کنیم.
    # نام Sorted Set ما (مثلاً برای بازی دوز):
    leaderboard_key = f"leaderboard:{score_input.game_type}"
    
    # امتیاز کاربر رو در Sorted Set ذخیره می‌کنیم.
    # کلید عضو (member) می‌تونه user_id باشه. Redis امتیازات تکراری برای یک عضو رو آپدیت می‌کنه.
    # اگر بخوایم فقط بالاترین امتیاز ثبت بشه، باید قبلش چک کنیم.
    # برای سادگی، فعلاً هر امتیاز جدید رو اضافه می‌کنیم (یا آپدیت اگر قبلاً بوده).
    # Redis zadd: اگر عضو وجود داشته باشه، امتیازش آپدیت میشه.
    # اگر می‌خوایم فقط وقتی امتیاز جدید بیشتره آپدیت بشه، باید از آپشن‌های ZADD (مثل GT یا LT در Redis 7+) استفاده کنیم
    # یا قبلش امتیاز فعلی رو بخونیم و مقایسه کنیم. کتابخانه vercel_kv ممکنه همه آپشن‌های ZADD رو نداشته باشه.
    
    # برای سادگی فعلاً فقط بهترین امتیاز هر کاربر رو نگه میداریم.
    # ابتدا امتیاز فعلی کاربر رو می‌گیریم
    try:
        # vercel_kv از طریق متغیرهای محیطی به صورت خودکار کانفیگ میشه
        kv_store = KV() # این باید به طور خودکار از متغیرهای محیطی KV_URL و KV_REST_API_TOKEN استفاده کنه

        current_score_bytes = await kv_store.zscore(leaderboard_key, str(user_id))
        current_score = int(current_score_bytes.decode()) if current_score_bytes else -1 # اگر امتیازی نداشته، -1

        if score_input.score > current_score:
            # امتیاز جدید بهتره، پس آپدیت می‌کنیم
            # ZADD member باید رشته باشه. امتیاز باید float یا int باشه.
            await kv_store.zadd(leaderboard_key, {str(user_id): float(score_input.score)})
            print(f"Score for user {user_id} updated to {score_input.score} in {leaderboard_key}")
            action_taken = "updated"
        else:
            print(f"New score {score_input.score} is not higher than current {current_score} for user {user_id}. Not updated.")
            action_taken = "not_updated_lower_score"
        
        # می‌تونیم برای هر کاربر، اطلاعاتش (مثل نام) رو هم جداگانه ذخیره کنیم اگر لازم شد
        # مثلاً با یک کلید دیگه: user_info:<user_id>
        user_info_key = f"user_info:{user_id}"
        await kv_store.set(user_info_key, json.dumps({"username": username, "first_name": first_name}))
        
        return {
            "status": "success", 
            "message": f"Score processed for user {user_id}. Action: {action_taken}",
            "user_id": user_id,
            "submitted_score": score_input.score,
            "previous_score": current_score if current_score != -1 else None,
            "leaderboard_key": leaderboard_key
        }

    except Exception as e:
        print(f"Error interacting with KV store: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving score: {e}")

# (اختیاری) یک روت برای تست اینکه آیا تابع score.py دیپلوی شده
@app.get("/api/score_test")
async def score_test():
    return {"message": "Score API endpoint is active."}
