import os
import asyncio
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from googletrans import Translator

# 读取机器人 Token（Render 会自动填）
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL") + WEBHOOK_PATH

# 初始化
translator = Translator()
app = FastAPI()
bot_app = ApplicationBuilder().token(TOKEN).build()

# 翻译函数（和原来一样）
async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        return
    detected = translator.detect(text)
    src_lang = detected.lang
    target_lang = "en" if src_lang.startswith("zh") else "zh-cn"
    result = translator.translate(text, dest=target_lang)
    await update.message.reply_text(
        f"检测语言：{src_lang}\n"
        f"翻译为：{target_lang}\n"
        f"结果：{result.text}"
    )

# 注册消息处理
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_message))

# 接收 Telegram 消息
@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    json_data = await request.json()
    update = Update.de_json(json_data, bot_app.bot)
    await bot_app.update_queue.put(update)
    return Response(content="OK", status_code=200)

# 启动时设置 Webhook
@app.on_event("startup")
async def on_startup():
    await bot_app.bot.delete_webhook(drop_pending_updates=True)
    await bot_app.bot.set_webhook(url=WEBHOOK_URL)
    asyncio.create_task(bot_app.start())
    print(f"Webhook 设置成功：{WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot_app.stop()