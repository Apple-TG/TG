import os
import re  # 新增：用于语言检测
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

# ---------- 翻译函数（优化版） ----------
async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        return
    try:
        # 改进语言检测：检查中文汉字或英文
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
        has_english = bool(re.search(r'[a-zA-Z]', text))
        
        if has_chinese:
            from_lang = "zh"
            to_lang = "en"
            detected_lang = "zh"
        elif has_english:
            from_lang = "en"
            to_lang = "zh"
            detected_lang = "en"
        else:
            # 其他语言/符号，默认英→中
            from_lang = "en"
            to_lang = "zh"
            detected_lang = "unknown"
        
        # 创建翻译器
        translator = Translator(from_lang=from_lang, to_lang=to_lang)
        result = translator.translate(text)
        
        await update.message.reply_text(
            f"检测语言：{detected_lang}\n"
            f"翻译为：{to_lang}\n"
            f"结果：{result}"
        )
    except Exception as e:
        # 强制回复错误（调试用）
        await update.message.reply_text(
            f"翻译出错：{str(e)}\n"
            f"原消息：{text[:50]}...\n"
            f"（可能是网络限流，稍后重试）"
        )
        print(f"翻译错误日志: {e}")  # Render 日志可见

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
    return {"status": "ok", "webhook_url": WEBHOOK_URL, "translator": "translate (优化版)"}
