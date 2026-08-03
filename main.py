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

from pdf2docx import Converter
from pdf2image import convert_from_path
from PIL import Image
import pdfplumber
import pandas as pd
import fitz  # PyMuPDF for compression
from pypdf import PdfReader, PdfWriter

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ---------------------------------------------------------
# Flask Web Server setup (Keep alive for Render)
# ---------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "All Doc Converter Bot is Active 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

USER_FILES = {}

# ---------------------------------------------------------
# Telegram Bot Handlers
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "✨ *Welcome to All Doc Converter Bot!* ⚡\n\n"
        "Your ultimate assistant for fast and easy document processing.\n\n"
        "📌 *Supported Services:*\n"
        "├ 📄 ➔ 📝 *PDF to Word* (.docx)\n"
        "├ 📄 ➔ 📊 *PDF to Excel* (.xlsx)\n"
        "├ 📝 ➔ 📄 *Word to PDF* (.pdf)\n"
        "├ 🖼 ➔ 📄 *Image to PDF* (.pdf)\n"
        "├ 📄 ➔ 🖼 *PDF to Images* (PNG)\n"
        "├ 🗜 *Compress PDF* (Reduce size)\n"
        "└ 🔓 *Remove Password* (Unlock PDF)\n\n"
        "📥 *How to use:* Send any **PDF**, **Word (.docx)**, or **Image** file to begin!"
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file_name = doc.file_name if doc.file_name else "file"
    file_ext = os.path.splitext(file_name)[1].lower()

    status_msg = await update.message.reply_text("📥 *Downloading file... Please wait.*", parse_mode="Markdown")
    
    file = await context.bot.get_file(doc.file_id)
    input_path = f"downloads_{update.effective_user.id}_{file_name}"
    await file.download_to_drive(input_path)
    
    USER_FILES[update.effective_user.id] = {
        'file_path': input_path,
        'file_name': file_name
    }

    # PDF File received
    if file_ext == '.pdf':
        keyboard = [
            [
                InlineKeyboardButton("📄 Convert to Word (.docx)", callback_data="convert_word"),
                InlineKeyboardButton("📊 Convert to Excel (.xlsx)", callback_data="convert_excel")
            ],
            [
                InlineKeyboardButton("🖼 Convert to Images (PNG)", callback_data="convert_image"),
                InlineKeyboardButton("🗜 Compress PDF", callback_data="compress_pdf")
            ],
            [
                InlineKeyboardButton("🔓 Remove Password", callback_data="remove_pass")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await status_msg.edit_text(
            f"📁 *Received PDF:* `{file_name}`\n\nChoose an action below:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    # Word File received (.docx)
    elif file_ext in ['.docx', '.doc']:
        keyboard = [
            [
                InlineKeyboardButton("📄 Convert to PDF", callback_data="word_to_pdf")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await status_msg.edit_text(
            f"📁 *Received Word Document:* `{file_name}`\n\nChoose conversion format:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await status_msg.edit_text("❌ Unsupported file format. Please send a PDF, Word (.docx), or Image file.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    status_msg = await update.message.reply_text("📥 *Downloading Image...*", parse_mode="Markdown")
    
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
        "🖼 *Image Received!* Choose conversion option:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    action = query.data
    
    if user_id not in USER_FILES:
        await query.edit_message_text("❌ *Session expired.* Please re-send your file.", parse_mode="Markdown")
        return

    user_data = USER_FILES[user_id]
    input_path = user_data['file_path']
    file_name = user_data['file_name']

    # --- PDF TO WORD ---
    if action == "convert_word":
        await query.edit_message_text("⏳ *Converting PDF to Word (.docx)...*", parse_mode="Markdown")
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
            await query.edit_message_text("✅ *Conversion complete!* Sent your Word file above.", parse_mode="Markdown")
            if os.path.exists(output_docx): os.remove(output_docx)
        except Exception as e:
            logging.error(f"Error PDF to Word: {e}")
            await query.edit_message_text("❌ Failed to convert PDF to Word.")

    # --- PDF TO EXCEL ---
    elif action == "convert_excel":
        await query.edit_message_text("⏳ *Extracting tables & converting to Excel (.xlsx)...*", parse_mode="Markdown")
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
                await query.edit_message_text("✅ *PDF successfully converted to Excel!*", parse_mode="Markdown")
                if os.path.exists(output_xlsx): os.remove(output_xlsx)
            else:
                await query.edit_message_text("⚠️ No readable tables found in this PDF.")
        except Exception as e:
            logging.error(f"Error PDF to Excel: {e}")
            await query.edit_message_text("❌ Failed to convert PDF to Excel.")

    # --- COMPRESS PDF ---
    elif action == "compress_pdf":
        await query.edit_message_text("⏳ *Compressing PDF file size...*", parse_mode="Markdown")
        output_compressed = f"{os.path.splitext(input_path)[0]}_compressed.pdf"
        try:
            doc = fitz.open(input_path)
            doc.save(output_compressed, garbage=4, deflate=True, clean=True)
            doc.close()

            with open(output_compressed, 'rb') as pdf_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=pdf_file,
                    filename=f"{os.path.splitext(file_name)[0]}_compressed.pdf"
                )
            await query.edit_message_text("✅ *PDF successfully compressed!*", parse_mode="Markdown")
            if os.path.exists(output_compressed): os.remove(output_compressed)
        except Exception as e:
            logging.error(f"Error Compress PDF: {e}")
            await query.edit_message_text("❌ Failed to compress PDF.")

    # --- REMOVE PASSWORD ---
    elif action == "remove_pass":
        await query.edit_message_text("⏳ *Removing password protection...*", parse_mode="Markdown")
        output_unlocked = f"{os.path.splitext(input_path)[0]}_unlocked.pdf"
        try:
            reader = PdfReader(input_path)
            if reader.is_encrypted:
                # Attempt to decrypt with empty password if restrictions are simple
                reader.decrypt("")
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            with open(output_unlocked, "wb") as f:
                writer.write(f)

            with open(output_unlocked, 'rb') as pdf_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=pdf_file,
                    filename=f"{os.path.splitext(file_name)[0]}_unlocked.pdf"
                )
            await query.edit_message_text("✅ *PDF Password restrictions removed!*", parse_mode="Markdown")
            if os.path.exists(output_unlocked): os.remove(output_unlocked)
        except Exception as e:
            logging.error(f"Error Remove Pass: {e}")
            await query.edit_message_text("❌ Failed to unlock PDF. If it requires a custom password, decrypting without it is restricted.")

    # --- PDF TO IMAGES ---
    elif action == "convert_image":
        await query.edit_message_text("⏳ *Exporting PDF pages as Images...*", parse_mode="Markdown")
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
            await query.edit_message_text("✅ *PDF pages sent as Images!*", parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Error PDF to Image: {e}")
            await query.edit_message_text("❌ Failed to convert PDF to Images.")

    # --- IMAGE TO PDF ---
    elif action == "img_to_pdf":
        await query.edit_message_text("⏳ *Converting Image to PDF...*", parse_mode="Markdown")
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
            await query.edit_message_text("✅ *Image successfully converted to PDF!*", parse_mode="Markdown")
            if os.path.exists(output_pdf): os.remove(output_pdf)
        except Exception as e:
            logging.error(f"Error Image to PDF: {e}")
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
