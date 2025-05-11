from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware 
from pydantic import BaseModel, Field
import os
from upstash_redis.asyncio import Redis as UpstashAsyncRedis 
import hashlib
import hmac
from urllib.parse import parse_qsl
import json
from typing import Optional, List # List اضافه شد

app = FastAPI()

# ---------- شروع پیکربندی CORS ----------
origins = [
    "https://mynameiskaveh.github.io", 
    # "http://localhost:3000", # برای تست محلی اگر نیاز شد
    # "http://127.0.0.1:3000", # برای تست محلی اگر نیاز شد
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
    game_type: Optional[str] = "tictactoe_default_v1" # نام پیش‌فرض رو هم اینجا گذاشتم
    initData: str = Field(..., alias="telegramInitData")

# مدل داده برای آیتم‌های لیدربورد (برای پاسخ API)
class LeaderboardEntry(BaseModel):
    user_id: str
    name: str
    score: int

class LeaderboardResponse(BaseModel):
    leaderboard: List[LeaderboardEntry]
    game_type: str
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

    user_id = str(user_data['id'])
    username = user_data.get('username', f"user_{user_id}")
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
        print(f"Error interacting with Async Redis (Upstash): {e}")
        raise HTTPException(status_code=500, detail=f"Error saving score: {e}")

@app.get("/api/score_test")
async def score_test():
    if not redis_client:
        return {"message": "Score API active, but Async Redis client not initialized (check KV_REST_API_URL & KV_REST_API_TOKEN env vars)."}
    try:
        pong = await redis_client.ping()
        return {"message": f"Score API endpoint is active and Async Redis connection is OK. PING response: {pong}"}
    except Exception as e:
        return {"message": f"Score API endpoint is active, but Async Redis PING failed: {e} (Check KV_REST_API_URL & KV_REST_API_TOKEN)"}

# ---------- API Endpoint برای گرفتن لیدربورد ----------
@app.get("/api/leaderboard", response_model=LeaderboardResponse) # اضافه کردن response_model
async def get_leaderboard(
    game_type: str = "tictactoe_default_v1", 
    limit: int = 10 
):
    print(f"Received request for leaderboard: GameType={game_type}, Limit={limit}")

    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis client not initialized. Check KV/Redis env vars.")

    leaderboard_key = f"leaderboard:{game_type}"
    leaderboard_data: List[LeaderboardEntry] = [] # مشخص کردن تایپ

    try:
        top_players_with_scores_tuples = await redis_client.zrevrange(
            leaderboard_key, 
            0, 
            limit - 1, 
            withscores=True
        )
        # نتیجه به صورت لیستی از بایت‌هاست: [b'user_id1', b'score1', b'user_id2', b'score2', ...]
        # باید اونها رو به صورت جفت جدا کنیم

        if not top_players_with_scores_tuples:
            print(f"No data found for leaderboard: {leaderboard_key}")
            return LeaderboardResponse(leaderboard=[], game_type=game_type, message="لیدربورد خالی است.")

        print(f"Fetched top players (raw) from Redis: {top_players_with_scores_tuples}")

        # تبدیل لیست فلت به لیست تاپل‌ها (user_id, score)
        # کتابخانه upstash-redis با withscores=True لیستی از [member, score, member, score, ...] برمی‌گرداند
        # که همه بایت هستند.
        
        i = 0
        while i < len(top_players_with_scores_tuples):
            user_id_bytes = top_players_with_scores_tuples[i]
            score_bytes = top_players_with_scores_tuples[i+1]
            i += 2

            user_id_str = user_id_bytes.decode('utf-8')
            score_float = float(score_bytes.decode('utf-8'))
            
            user_info_key = f"user_info:{user_id_str}"
            user_info_json_bytes = await redis_client.get(user_info_key)
            
            player_name = f"User {user_id_str}"
            if user_info_json_bytes:
                try:
                    user_info = json.loads(user_info_json_bytes.decode('utf-8'))
                    player_name = user_info.get('first_name', user_info.get('username', player_name))
                except json.JSONDecodeError:
                    print(f"Could not decode user_info for {user_id_str}")
            
            leaderboard_data.append(
                LeaderboardEntry(user_id=user_id_str, name=player_name, score=int(score_float))
            )
            
        return LeaderboardResponse(leaderboard=leaderboard_data, game_type=game_type)

    except Exception as e:
        print(f"Error fetching leaderboard from Redis: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching leaderboard: {e}")
