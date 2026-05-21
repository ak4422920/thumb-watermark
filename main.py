
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
from flask import Flask
import threading
import os

from config import API_TOKEN
from database import init_db, close_db
from plugins import start_router, settings_router, video_router, admin_router
from plugins.canvas import router as canvas_router
from plugins.poster import router as poster_router

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Is order mein rakho bhai
dp.include_router(admin_router)   # Admin hamesha VIP, sabse upar
dp.include_router(start_router)
dp.include_router(settings_router)
dp.include_router(video_router)
dp.include_router(canvas_router)
dp.include_router(poster_router)
app = Flask(__name__)


@app.route("/")
def home():
    return "Bot Made By @AkMovieVerse"


def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


async def main():
    # Initialize database
    await init_db()
    print("🚀 Bot is starting...")
    
    try:
        await dp.start_polling(bot)
    finally:
        await close_db()


if __name__ == "__main__":
    print(r"""
   ______            __                  __  __        ____        __       
  / ____/___ _____  / /_____ _________  / / / /___ _  / __ )____  / /______ 
 / /   / __ `/ __ \/ __/ __ `/ ___/ _ \/ / / / __ `/ / __  / __ \/ __/ ___/ 
/ /___/ /_/ / / / / /_/ /_/ / /  /  __/ / / / /_/ / / /_/ / /_/ / /_(__  )  
\____/\__,_/_/ /_/\__/\__,_/_/   \___/_/_/_/\__,_/ /_____/\____/\__/____/   
                                                                            
      BOT WORKING PROPERLY....
    """)
    print("Starting Bot...")
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
