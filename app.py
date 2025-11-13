import os
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from libretranslatepy import LibreTranslateAPI

# ---------- 环境变量 ----------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN 未设置！")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{os.getenv('RENDER_EXTERNAL_URL')}{WEBHOOK_PATH}"

app = FastAPI()
bot_app = ApplicationBuilder().token(TOKEN).build()

# ---------- 翻译器（免费公共服务器） ----------
translator = LibreTranslateAPI("https://libretranslate.de")

# ---------- 翻译函数 ----------
async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        return
    try:
        # 检测语言
        detect_result = translator.detect(text)
        src_lang = detect_result[0]["language"]  # 如 'en', 'zh'
        
        # 决定目标语言
        target_lang = "en" if src_lang == "zh" else "zh"
        
        # 执行翻译
        result = translator.translate(text, src_lang, target_lang)
        
        await update.message.reply_text(
            f"检测语言：{src_lang}\n"
            f"翻译为：{target_lang}\n"
            f"结果：{result}"
        )
    except Exception as e:
        await update.message.reply_text(f"翻译出错：{str(e)}\n（公共服务器可能繁忙，稍后重试）")

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
    return {"status": "ok", "webhook_url": WEBHOOK_URL, "translator": "LibreTranslate (免费)"}
