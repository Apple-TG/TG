import os
import asyncio
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator

# ---------- 环境变量 ----------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN 未设置！去 Render 加环境变量！")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{os.getenv('RENDER_EXTERNAL_URL')}{WEBHOOK_PATH}"

# ---------- 初始化 ----------
app = FastAPI()
bot_app = ApplicationBuilder().token(TOKEN).build()

# ---------- 翻译函数 ----------
async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        return

    try:
        # 动态创建翻译器
        translator = GoogleTranslator(source='auto')
        detected = translator.detect(text)
        src_lang = detected

        target_lang = "en" if src_lang.startswith("zh") else "zh-CN"
        result = translator.translate(text, target=target_lang)

        await update.message.reply_text(
            f"检测语言：{src_lang}\n"
            f"翻译为：{target_lang}\n"
            f"结果：{result}"
        )
    except Exception as e:
        await update.message.reply_text(f"翻译出错：{str(e)}")

# 注册
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_message))

# ---------- Webhook ----------
@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    try:
        json_data = await request.json()
        update = Update.de_json(json_data, bot_app.bot)
        await bot_app.process_update(update)
    except Exception as e:
        print(f"Webhook 错误: {e}")
    return Response(content="OK", status_code=200)

# ---------- 启动 ----------
@app.on_event("startup")
async def on_startup():
    try:
        await bot_app.bot.delete_webhook(drop_pending_updates=True)
        await bot_app.bot.set_webhook(url=WEBHOOK_URL)
        await bot_app.start()
        print(f"Webhook 设置成功：{WEBHOOK_URL}")
    except Exception as e:
        print(f"启动失败: {e}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot_app.stop()
    await bot_app.shutdown()

# ---------- 健康检查 ----------
@app.get("/")
async def health():
    return {"status": "ok", "message": "翻译机器人已启动！"}
