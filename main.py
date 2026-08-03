import os
import logging
import asyncio
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

from pdf2docx import Converter
from pdf2image import convert_from_path
from PIL import Image
import pdfplumber
import pandas as pd

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

USER_FILES = {}

# ---------------------------------------------------------
# Telegram Bot Handlers
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "Welcome to All-in-one Ethio PDF Converter! 🇪🇹\n\n"
        "I can help you convert and process your documents:\n\n"
        "📌 *Available Services:*\n"
        "• 📄 *PDF to Word* (.docx)\n"
        "• 📊 *PDF to Excel* (.xlsx)\n"
        "• 🖼 *PDF to Images* (PNG)\n"
        "• 🖼➡️📄 *Image to PDF*\n\n"
        "📥 *How to use:* Simply send any PDF or Image file to start!"
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file_name = doc.file_name if doc.file_name else "document.pdf"
    
    if file_name.lower().endswith('.pdf'):
        status_msg = await update.message.reply_text("📥 Downloading PDF file...")
        
        file = await context.bot.get_file(doc.file_id)
        input_path = f"downloads_{update.effective_user.id}_{file_name}"
        await file.download_to_drive(input_path)
        
        USER_FILES[update.effective_user.id] = {
            'file_path': input_path,
            'file_name': file_name
        }
        
        keyboard = [
            [
                InlineKeyboardButton("📄 Convert to Word (.docx)", callback_data="convert_word"),
                InlineKeyboardButton("📊 Convert to Excel (.xlsx)", callback_data="convert_excel")
            ],
            [
                InlineKeyboardButton("🖼 Convert to Images (PNG)", callback_data="convert_image")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await status_msg.edit_text(
            f"✅ File Received: *{file_name}*\n\nSelect an option below:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("Please send a valid PDF file or Image.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    status_msg = await update.message.reply_text("📥 Downloading Image...")
    
    file = await context.bot.get_file(photo.file_id)
    input_path = f"downloads_{update.effective_user.id}_photo.jpg"
    await file.download_to_drive(input_path)
    
    USER_FILES[update.effective_user.id] = {
        'file_path': input_path,
        'file_name': "photo.jpg"
    }
    
    keyboard = [
        [
            InlineKeyboardButton("📄 Convert to PDF", callback_data="img_to_pdf")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await status_msg.edit_text(
        "✅ Image Received! Choose an option:",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    action = query.data
    
    if user_id not in USER_FILES:
        await query.edit_message_text("❌ File session expired. Please re-send your PDF/Image.")
        return

    user_data = USER_FILES[user_id]
    input_path = user_data['file_path']
    file_name = user_data['file_name']

    # --- PDF TO WORD ---
    if action == "convert_word":
        await query.edit_message_text("⏳ Converting PDF to Word (.docx)... Please wait.")
        output_docx = f"{os.path.splitext(input_path)[0]}.docx"
        try:
            cv = Converter(input_path)
            cv.convert(output_docx, start=0, end=None)
            cv.close()
            
            with open(output_docx, 'rb') as docx_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=docx_file,
                    filename=f"{os.path.splitext(file_name)[0]}.docx"
                )
            await query.edit_message_text("✅ Conversion complete! Word document sent above.")
            if os.path.exists(output_docx): os.remove(output_docx)
        except Exception as e:
            logging.error(f"Error in PDF to Word: {e}")
            await query.edit_message_text("❌ Failed to convert PDF to Word.")

    # --- PDF TO EXCEL ---
    elif action == "convert_excel":
        await query.edit_message_text("⏳ Extracting tables & converting PDF to Excel (.xlsx)...")
        output_xlsx = f"{os.path.splitext(input_path)[0]}.xlsx"
        try:
            all_tables = []
            with pdfplumber.open(input_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        df = pd.DataFrame(table[1:], columns=table[0])
                        all_tables.append(df)
            
            if all_tables:
                with pd.ExcelWriter(output_xlsx, engine='openpyxl') as writer:
                    for idx, df in enumerate(all_tables):
                        df.to_excel(writer, sheet_name=f"Table_{idx+1}", index=False)
                
                with open(output_xlsx, 'rb') as xlsx_file:
                    await context.bot.send_document(
                        chat_id=query.message.chat_id,
                        document=xlsx_file,
                        filename=f"{os.path.splitext(file_name)[0]}.xlsx"
                    )
                await query.edit_message_text("✅ PDF successfully converted to Excel!")
                if os.path.exists(output_xlsx): os.remove(output_xlsx)
            else:
                await query.edit_message_text("⚠️ No readable tables found in this PDF.")
        except Exception as e:
            logging.error(f"Error in PDF to Excel: {e}")
            await query.edit_message_text("❌ Failed to convert PDF to Excel.")

    # --- PDF TO IMAGES ---
    elif action == "convert_image":
        await query.edit_message_text("⏳ Converting PDF pages to Images...")
        try:
            images = convert_from_path(input_path)
            for i, img in enumerate(images[:5]):
                img_path = f"page_{i+1}.png"
                img.save(img_path, 'PNG')
                with open(img_path, 'rb') as img_file:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=img_file,
                        caption=f"Page {i+1}"
                    )
                if os.path.exists(img_path): os.remove(img_path)
            await query.edit_message_text("✅ Pages exported as Images!")
        except Exception as e:
            logging.error(f"Error in PDF to Image: {e}")
            await query.edit_message_text("❌ Failed to convert PDF to Images.")

    # --- IMAGE TO PDF ---
    elif action == "img_to_pdf":
        await query.edit_message_text("⏳ Converting Image to PDF...")
        output_pdf = f"{os.path.splitext(input_path)[0]}.pdf"
        try:
            image = Image.open(input_path)
            image_converted = image.convert('RGB')
            image_converted.save(output_pdf)
            
            with open(output_pdf, 'rb') as pdf_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=pdf_file,
                    filename="converted_photo.pdf"
                )
            await query.edit_message_text("✅ Image successfully converted to PDF!")
            if os.path.exists(output_pdf): os.remove(output_pdf)
        except Exception as e:
            logging.error(f"Error in Image to PDF: {e}")
            await query.edit_message_text("❌ Failed to convert Image to PDF.")

    if os.path.exists(input_path):
        os.remove(input_path)
    del USER_FILES[user_id]

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
