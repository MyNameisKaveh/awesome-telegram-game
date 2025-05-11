from fastapi import FastAPI, Request, HTTPException, Depends
from pydantic import BaseModel, Field
import os
from upstash_redis import Redis # <<< تغییر: استفاده از upstash-redis
import hashlib
import hmac
from urllib.parse import parse_qsl
import json # json رو اضافه کردم چون در validate_init_data استفاده شده بود
from typing import Optional

app = FastAPI()

class ScoreData(BaseModel):
    score: int
    game_type: Optional[str] = "tictactoe_default"
    initData: str = Field(..., alias="telegramInitData")

# خواندن متغیرهای محیطی برای Upstash Redis
# کتابخانه upstash-redis به طور خودکار این‌ها رو می‌خونه اگر درست تنظیم شده باشن
# یا می‌تونیم مستقیماً بهش پاس بدیم
UPSTASH_REDIS_REST_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# ساختن یک نمونه از کلاینت Redis
# اگر متغیرهای محیطی به طور خودکار خوانده نشن، باید به صورت دستی پاس داده بشن:
if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
    redis_client = Redis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN)
    print("Upstash Redis client initialized.")
else:
    redis_client = None
    print("CRITICAL: Upstash Redis environment variables not found! KV store will not work.")


def validate_init_data(init_data_str: str, bot_token: str) -> Optional[dict]:
    if not bot_token:
        print("Error: BOT_TOKEN not available for initData validation.")
        return None
    try:
        parsed_data = dict(parse_qsl(init_data_str))
    except Exception as e:
        print(f"Error parsing initData string: {e}")
        return None
    if "hash" not in parsed_data:
        print("Error: 'hash' not found in initData.")
        return None
    received_hash = parsed_data.pop("hash")
    data_check_string_parts = []
    for key, value in sorted(parsed_data.items()):
        data_check_string_parts.append(f"{key}={value}")
    data_check_string = "\n".join(data_check_string_parts)
    secret_key = hmac.new("WebAppData".encode(), bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if calculated_hash == received_hash:
        print("initData validation successful.")
        if 'user' in parsed_data:
            try:
                user_info_str = parsed_data['user']
                # گاهی اوقات user_info_str خودش unquote شده، گاهی نه.
                # برای اطمینان، unquote می‌کنیم اگر درصد (%) درش بود
                # from urllib.parse import unquote as url_unquote
                # if '%' in user_info_str:
                #    user_info_str = url_unquote(user_info_str)
                user_info = json.loads(user_info_str)
                return user_info
            except json.JSONDecodeError as e:
                print(f"Error decoding 'user' field from initData: {e}. Value was: {parsed_data.get('user')}")
                return None
        else:
            print("Warning: 'user' field not found in parsed_data after validation.")
            return None
    else:
        print(f"initData validation failed. Calculated: {calculated_hash}, Received: {received_hash}")
        return None

@app.post("/api/submit_score")
async def submit_score(score_input: ScoreData, request: Request):
    print(f"Received score submission: Score={score_input.score}, GameType={score_input.game_type}")
    
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis client not initialized. Check KV/Redis env vars.")

    user_data = validate_init_data(score_input.initData, BOT_TOKEN)
    if not user_data or 'id' not in user_data:
        print("Score submission rejected: Invalid or missing user data from initData.")
        raise HTTPException(status_code=403, detail="Invalid user authentication (initData).")

    user_id = str(user_data['id']) # Redis member باید رشته باشه
    username = user_data.get('username', f"user_{user_id}")
    first_name = user_data.get('first_name', "Player")

    print(f"Score submitted by User ID: {user_id}, Username: {username}, First Name: {first_name}")

    leaderboard_key = f"leaderboard:{score_input.game_type}"
    
    try:
        # گرفتن امتیاز فعلی کاربر از Sorted Set
        current_score_tuple = await redis_client.zscore(leaderboard_key, user_id)
        current_score = float(current_score_tuple) if current_score_tuple is not None else -1.0

        if score_input.score > current_score:
            # اضافه کردن یا آپدیت امتیاز در Sorted Set
            # ZADD key score member
            await redis_client.zadd(leaderboard_key, {user_id: float(score_input.score)})
            print(f"Score for user {user_id} updated to {score_input.score} in {leaderboard_key}")
            action_taken = "updated"
        else:
            print(f"New score {score_input.score} is not higher than current {current_score} for user {user_id}. Not updated.")
            action_taken = "not_updated_lower_score"
        
        user_info_key = f"user_info:{user_id}"
        # ذخیره اطلاعات کاربر (می‌تونید از JSON string یا HSET استفاده کنید)
        await redis_client.set(user_info_key, json.dumps({"username": username, "first_name": first_name}))
        
        return {
            "status": "success", 
            "message": f"Score processed for user {user_id}. Action: {action_taken}",
            "user_id": user_id,
            "submitted_score": score_input.score,
            "previous_score": current_score if current_score != -1.0 else None,
            "leaderboard_key": leaderboard_key
        }

    except Exception as e:
        print(f"Error interacting with Redis (Upstash): {e}")
        raise HTTPException(status_code=500, detail=f"Error saving score: {e}")

@app.get("/api/score_test")
async def score_test():
    if not redis_client:
        return {"message": "Score API active, but Redis client not initialized (check env vars)."}
    try:
        # یک عملیات ساده برای تست اتصال به Redis
        await redis_client.ping()
        return {"message": "Score API endpoint is active and Redis connection is OK."}
    except Exception as e:
        return {"message": f"Score API endpoint is active, but Redis PING failed: {e}"}
