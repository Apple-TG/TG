import os
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from translate import Translator

# ---------- 环境变量 ----------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN 未设置！")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{os.getenv('RENDER_EXTERNAL_URL')}{WEBHOOK_PATH}"

app = FastAPI()
bot_app = ApplicationBuilder().token(TOKEN).build()

# ---------- 翻译函数 ----------
async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        return
    try:
        # 简单判断：含中文 → 翻译为英文，否则翻译为中文
        is_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)
        from_lang = "zh" if is_chinese else "en"
        to_lang = "en" if is_chinese else "zh"
        
        # 创建翻译器
        translator = Translator(from_lang=from_lang, to_lang=to_lang)
        result = translator.translate(text)
        
        await update.message.reply_text(
            f"检测语言：{from_lang}\n"
            f"翻译为：{to_lang}\n"
            f"结果：{result}"
        )
    except Exception as e:
        await update.message.reply_text(f"翻译出错：{str(e)}\n（网络波动，稍后重试）")

bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_message))

# ---------- Webhook ----------
@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    print("收到 Telegram Webhook！")
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
    print("正在初始化 Application...")
    try:
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.bot.delete_webhook(drop_pending_updates=True)
        await bot_app.bot.set_webhook(url=WEBHOOK_URL)
        print(f"Webhook 设置成功：{WEBHOOK_URL}")
    except Exception as e:
        print(f"启动失败: {e}")

@app.on_event("shutdown")
async def on_shutdown():
    print("正在关闭 Application...")
    try:
        await bot_app.stop()
        await bot_app.shutdown()
    except Exception as e:
        print(f"关闭失败: {e}")

# ---------- 测试接口 ----------
@app.get("/")
async def home():
    return {"message": "机器人已启动！访问 /test"}

@app.get("/test")
async def test():
    return {"status": "ok", "webhook_url": WEBHOOK_URL, "translator": "translate (稳定)"}
