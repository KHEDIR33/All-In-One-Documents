import os
import logging
from threading import Thread
from flask import Flask

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ---------------------------------------------------------
# Flask Web Server setup
# ---------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Ethio PDF Converter Bot is running active 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ---------------------------------------------------------
# Telegram Bot Handlers
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "Welcome to All-in-one Ethio PDF Converter! 🇪🇹\n\n"
        "Please send your PDF file or Image to get started."
    )
    await update.message.reply_text(welcome_msg)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file_name = doc.file_name if doc.file_name else ""
    
    if file_name.lower().endswith('.pdf'):
        keyboard = [
            [
                InlineKeyboardButton("📄 Convert to Word (.docx)", callback_data="convert_word"),
                InlineKeyboardButton("🖼 Convert to Images (PNG)", callback_data="convert_image")
            ],
            [
                InlineKeyboardButton("🗜 Compress PDF", callback_data="compress_pdf"),
                InlineKeyboardButton("🔒 Remove Password", callback_data="remove_pass")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"📥 Received PDF: *{file_name}*\n\nSelect an option below:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("Please send a valid PDF file or Image.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("📄 Convert to PDF", callback_data="img_to_pdf"),
            InlineKeyboardButton("🔍 Extract Text (OCR)", callback_data="ocr_extract")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📥 Photo received! Choose an option:",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "convert_word":
        await query.edit_message_text("⏳ Converting PDF to Word... Please wait.")
    elif action == "convert_image":
        await query.edit_message_text("⏳ Converting PDF to Images...")
    elif action == "compress_pdf":
        await query.edit_message_text("⏳ Compressing PDF file size...")
    elif action == "img_to_pdf":
        await query.edit_message_text("⏳ Converting Image to PDF...")
    elif action == "ocr_extract":
        await query.edit_message_text("⏳ Extracting text from Image...")
    else:
        await query.edit_message_text("Unknown option selected.")

# ---------------------------------------------------------
# Main Bot Execution
# ---------------------------------------------------------
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("Error: BOT_TOKEN Environment Variable is missing!")
        return

    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("Bot is starting polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
