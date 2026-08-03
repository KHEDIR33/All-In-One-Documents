import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "እንኳን ወደ All-in-one Ethio PDF Converter በሰላም መጡ! 🇪🇹\n\n"
        "ለመቀየር የሚፈልጉትን PDF ወይም ምስል (Image) ፋይል ይላኩልኝ።"
    )
    await update.message.reply_text(welcome_text)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ፋይሉ ደርሶኛል! በመቀየር ላይ ነው... እባክዎን ትንሽ ይጠብቁ።")

if __name__ == '__main__':
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN Environment Variable missing!")
    else:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_document))
        app.run_polling()
