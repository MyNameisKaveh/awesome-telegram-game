from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware 
from pydantic import BaseModel, Field
import os
from upstash_redis.asyncio import Redis as UpstashAsyncRedis 
import hashlib
import hmac
from urllib.parse import parse_qsl, unquote # unquote اضافه شد
import json
from typing import Optional, List, Dict, Any

app = FastAPI()

# ---------- شروع پیکربندی CORS ----------
origins = [
    "https://mynameiskaveh.github.io", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)
# ---------- پایان پیکربندی CORS ----------

class ScoreData(BaseModel):
    score: int
    game_type: Optional[str] = "tictactoe_default_v1"
    initData: str = Field(..., alias="telegramInitData")

class LeaderboardEntry(BaseModel):
    user_id: str
    username: str
    first_name: str
    score: int

class LeaderboardResponse(BaseModel):
    leaderboard: List[LeaderboardEntry]
    message: Optional[str] = None


KV_REST_API_URL = os.environ.get("KV_REST_API_URL")
KV_REST_API_TOKEN = os.environ.get("KV_REST_API_TOKEN")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

redis_client: Optional[UpstashAsyncRedis] = None

if KV_REST_API_URL and KV_REST_API_TOKEN:
    redis_client = UpstashAsyncRedis(url=KV_REST_API_URL, token=KV_REST_API_TOKEN)
    print(f"Upstash Async Redis client initialized. URL starts with: {KV_REST_API_URL[:20]}...")
else:
    print("CRITICAL: Vercel KV environment variables (KV_REST_API_URL, KV_REST_API_TOKEN) not found! KV store will not work.")

def validate_init_data(init_data_str: str, bot_token: str) -> Optional[Dict[str, Any]]:
    if not bot_token:
        print("Error: BOT_TOKEN not available for initData validation.")
        return None
    try:
        # initData ممکن است خودش URL encoded باشد، یا فقط مقادیر داخل آن.
        # parse_qsl مقادیر را unquote می‌کند. اگر کل initData انکود شده، اول باید unquote شود.
        # init_data_str_unquoted = unquote(init_data_str) # اگر لازم شد
        parsed_data = dict(parse_qsl(init_data_str)) # یا init_data_str_unquoted
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
                # مقادیر داخل فیلد user هم ممکنه URL-encoded باشن
                user_info_decoded_str = unquote(user_info_str) 
                user_info = json.loads(user_info_decoded_str)
                # اضافه کردن خود initData به اطلاعات کاربر برای دسترسی‌های بعدی اگر لازم شد
                # user_info['raw_init_data_user_field'] = user_info_str 
                # user_info['raw_init_data_parsed_excluding_hash'] = parsed_data 
                return user_info
            except json.JSONDecodeError as e:
                print(f"Error decoding 'user' field from initData: {e}. Value was: {parsed_data.get('user')}")
                return None
        else:
            print("Warning: 'user' field not found in parsed_data after validation.")
            return None
    else:
        print(f"initData validation FAILED. Calculated: {calculated_hash}, Received: {received_hash}")
        print(f"Data check string used for hash: \n{data_check_string}")
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

    user_id = str(user_data['id'])
    username = user_data.get('username', f"user_{user_id[:6]}")
    first_name = user_data.get('first_name', "Player")

    print(f"Score submitted by User ID: {user_id}, Username: {username}, First Name: {first_name}")

    leaderboard_key = f"leaderboard:{score_input.game_type}"
    
    try:
        current_score_tuple = await redis_client.zscore(leaderboard_key, user_id)
        current_score = float(current_score_tuple) if current_score_tuple is not None else -1.0

        if score_input.score > current_score:
            await redis_client.zadd(leaderboard_key, {user_id: float(score_input.score)})
            print(f"Score for user {user_id} updated to {score_input.score} in {leaderboard_key}")
            action_taken = "updated"
        else:
            print(f"New score {score_input.score} is not higher than current {current_score} for user {user_id}. Not updated.")
            action_taken = "not_updated_lower_score"
        
        user_info_key = f"user_info:{user_id}"
        user_info_to_store = {
            "username": username,
            "first_name": first_name,
            "language_code": user_data.get("language_code") 
        }
        await redis_client.set(user_info_key, json.dumps(user_info_to_store))
        
        return {
            "status": "success", 
            "message": f"Score processed for user {user_id}. Action: {action_taken}",
            "user_id": user_id,
            "submitted_score": score_input.score,
            "previous_score": current_score if current_score != -1.0 else None,
            "leaderboard_key": leaderboard_key
        }
    except Exception as e:
        print(f"Error interacting with Async Redis (Upstash) in submit_score: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving score: {e}")

@app.get("/api/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    game_type: str = "tictactoe_default_v1", 
    limit: int = 10 
):
    print(f"Received GET request for leaderboard: GameType={game_type}, Limit={limit}")

    if not redis_client:
        print("Error in get_leaderboard: Redis client not initialized.")
        raise HTTPException(status_code=500, detail="Redis client not initialized. Check KV/Redis env vars.")

    leaderboard_key = f"leaderboard:{game_type}"
    
    try:
        # zrevrange با withscores=True معمولاً لیستی از تاپل‌ها (عضو، امتیاز) برمی‌گرداند
        # مثال: [(b'user1', 100.0), (b'user2', 90.0)]
        raw_leaderboard_tuples: List[tuple[bytes, bytes]] = await redis_client.zrevrange( # تایپ دقیق‌تر
            leaderboard_key, 
            0, 
            limit - 1, 
            withscores=True 
        )

        print(f"Raw leaderboard data from Redis for key '{leaderboard_key}' (entries: {len(raw_leaderboard_tuples)}): {raw_leaderboard_tuples}")

        if not raw_leaderboard_tuples:
            print(f"Leaderboard for key '{leaderboard_key}' is empty.")
            return LeaderboardResponse(leaderboard=[], message="Leaderboard is empty for this game type.")

        leaderboard_data: List[LeaderboardEntry] = []
        
        # حالا روی تاپل‌ها حلقه می‌زنیم
        for user_id_bytes, score_bytes in raw_leaderboard_tuples:
            user_id = user_id_bytes.decode('utf-8') # مطمئن می‌شویم که بایت به رشته تبدیل می‌شود
            score_str = score_bytes.decode('utf-8') # امتیاز هم به رشته تبدیل می‌شود
            score = float(score_str) # سپس به float
            
            user_info_key = f"user_info:{user_id}"
            user_info_json_bytes = await redis_client.get(user_info_key)
            user_info_dict = {}
            if user_info_json_bytes:
                try:
                    user_info_data_str = user_info_json_bytes.decode('utf-8')
                    user_info_dict = json.loads(user_info_data_str)
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode user_info for user_id {user_id}. Raw data: {user_info_json_bytes}")
            
            leaderboard_data.append(LeaderboardEntry(
                user_id=user_id,
                username=user_info_dict.get("username", f"User...{user_id[-4:] if len(user_id) > 3 else user_id}"),
                first_name=user_info_dict.get("first_name", "Player"),
                score=int(score) 
            ))
        
        print(f"Leaderboard data prepared: Count={len(leaderboard_data)}")
        return LeaderboardResponse(leaderboard=leaderboard_data)

    except Exception as e:
        print(f"Error fetching or processing leaderboard from Redis: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching the leaderboard: {str(e)}")


@app.get("/api/score_test")
async def score_test():
    if not redis_client:
        return {"message": "Score API active, but Async Redis client not initialized (check KV_REST_API_URL & KV_REST_API_TOKEN env vars)."}
    try:
        pong = await redis_client.ping()
        return {"message": f"Score API endpoint is active and Async Redis connection is OK. PING response: {pong}"}
    except Exception as e:
        return {"message": f"Score API endpoint is active, but Async Redis PING failed: {e} (Check KV_REST_API_URL & KV_REST_API_TOKEN)"}
