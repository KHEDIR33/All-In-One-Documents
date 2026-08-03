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

# ---------------------------------------------------------
# Telegram Bot Handlers
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📄➡️📝 PDF to Word (.docx)", callback_data="info_pdf_word")],
        [InlineKeyboardButton("📄➡️📊 PDF to Excel (.xlsx)", callback_data="info_pdf_excel")],
        [InlineKeyboardButton("📝➡️📄 Word to PDF (.pdf)", callback_data="info_word_pdf")],
        [InlineKeyboardButton("🖼️➡️📄 Image to PDF (.pdf)", callback_data="info_img_pdf")],
        [InlineKeyboardButton("📄➡️🖼️ PDF to Images (PNG)", callback_data="info_pdf_img")],
        [InlineKeyboardButton("🗜️ Compress PDF (Reduce Size)", callback_data="info_compress")],
        [InlineKeyboardButton("🔓 Remove PDF Password", callback_data="info_unlock")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_msg = (
        "🤖 *Welcome to All Doc Converter Bot!* ⚡\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "አገልግሎት ለማግኘት የሚፈልጉትን **ፋይል (PDF, Word, Image)** ቀጥታ ወደዚህ ቻት ይላኩ!\n\n"
        "ወይም ስለ አገልግሎቶቹ ዝርዝር ለማየት ከታች ያሉትን **አዝራሮች (Buttons)** ይጫኑ፦"
    )
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file_name = doc.file_name if doc.file_name else "file"
    file_ext = os.path.splitext(file_name)[1].lower()

    status_msg = await update.message.reply_text("📥 *Downloading file... Please wait.*", parse_mode="Markdown")
    
    file = await context.bot.get_file(doc.file_id)
    input_path = f"downloads_{update.effective_user.id}_{file_name}"
    await file.download_to_drive(input_path)
    
    # ፋይሉን በ Context user_data ውስጥ እናስቀምጠዋለን (ጊዜያዊ)
    context.user_data['file_path'] = input_path
    context.user_data['file_name'] = file_name

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
    
    context.user_data['file_path'] = input_path
    context.user_data['file_name'] = "photo.jpg"
    
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

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_text = (
        "ለጽሁፍ መልእክትዎ ምላሽ መስጠት አልችልም። 😊\n\n"
        "እባክዎን መቀየር የሚፈልጉትን **ፋይል (PDF, Word ወይም Image)** ቀጥታ ይላኩልኝ!\n"
        "አገልግሎቶችን ለማየት `/start` ብለው ይጻፉ።"
    )
    await update.message.reply_text(msg_text, parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data

    if action.startswith("info_"):
        info_messages = {
            "info_pdf_word": "📄➡️📝 **PDF to Word**\n\nይህንን አገልግሎት ለመጠቀም መቀየር የሚፈልጉትን **PDF ፋይል** ቀጥታ ወደዚህ ቻት ይላኩ!",
            "info_pdf_excel": "📄➡️📊 **PDF to Excel**\n\nበ PDF ውስጥ ያሉ ሰንጠረዦችን ወደ Excel ለመቀየር **PDF ፋይሉን** ይላኩ!",
            "info_word_pdf": "📝➡️📄 **Word to PDF**\n\nየ Word ሰነድዎን ወደ PDF ለመቀየር **.docx ፋይልዎን** ይላኩ!",
            "info_img_pdf": "🖼️➡️📄 **Image to PDF**\n\nምስልን ወደ PDF ለመቀየር የሚፈልጉትን **ፎቶ/ምስል** ይላኩ!",
            "info_pdf_img": "📄➡️🖼️ **PDF to Images**\n\nየ PDF ገጾችን ወደ ምስል (PNG) ለመቀየር **PDF ፋይልዎን** ይላኩ!",
            "info_compress": "🗜️ **Compress PDF**\n\nየ PDF ፋይል መጠንን ለመቀነስ **PDF ፋይልዎን** ይላኩ!",
            "info_unlock": "🔓 **Remove Password**\n\nየተቆለፈ PDF ፓስወርድ ለማንሳት **PDF ፋይሉን** ይላኩ!"
        }
        msg = info_messages.get(action, "እባክዎን ለመጀመር ፋይልዎን ይላኩ።")
        await query.message.reply_text(msg, parse_mode="Markdown")
        return

    # ተጠቃሚው ዘግይቶ ሲመለስ ፋይሉ ከጠፋ / Session ከቀየረ እንደ አዲስ ማስጀመር
    if 'file_path' not in context.user_data or 'file_name' not in context.user_data:
        await query.edit_message_text(
            "⏳ ፋይሉ አልተገኘም ወይም ሰዎዎ (Session) አልቋል።\n\n"
            "እባክዎን `/start` ብለው በመጻፍ ወይም ፋይሉን እንደ አዲስ በመላክ ይጀምሩ!",
            parse_mode="Markdown"
        )
        return

    input_path = context.user_data['file_path']
    file_name = context.user_data['file_name']

    if action == "convert_word":
        await query.edit_message_text("⏳ *Converting PDF to Word (.docx)...*", parse_mode="Markdown")
        output_docx = f"{os.path.splitext(input_path)[0]}.docx"
        try:
            cv = Converter(input_path)
            cv.convert(output_docx, start=0, end=None)
            cv.close()
            with open(output_docx, 'rb') as docx_file:
                await context.bot.send_document(chat_id=query.message.chat_id, document=docx_file, filename=f"{os.path.splitext(file_name)[0]}.docx")
            await query.edit_message_text("✅ *Conversion complete!* Sent your Word file above.", parse_mode="Markdown")
            if os.path.exists(output_docx): os.remove(output_docx)
        except Exception as e:
            logging.error(f"Error PDF to Word: {e}")
            await query.edit_message_text("❌ Failed to convert PDF to Word.")

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
                    await context.bot.send_document(chat_id=query.message.chat_id, document=xlsx_file, filename=f"{os.path.splitext(file_name)[0]}.xlsx")
                await query.edit_message_text("✅ *PDF successfully converted to Excel!*", parse_mode="Markdown")
                if os.path.exists(output_xlsx): os.remove(output_xlsx)
            else:
                await query.edit_message_text("⚠️ No readable tables found in this PDF.")
        except Exception as e:
            logging.error(f"Error PDF to Excel: {e}")
            await query.edit_message_text("❌ Failed to convert PDF to Excel.")

    elif action == "compress_pdf":
        await query.edit_message_text("⏳ *Compressing PDF file size...*", parse_mode="Markdown")
        output_compressed = f"{os.path.splitext(input_path)[0]}_compressed.pdf"
        try:
            doc = fitz.open(input_path)
            doc.save(output_compressed, garbage=4, deflate=True, clean=True)
            doc.close()
            with open(output_compressed, 'rb') as pdf_file:
                await context.bot.send_document(chat_id=query.message.chat_id, document=pdf_file, filename=f"{os.path.splitext(file_name)[0]}_compressed.pdf")
            await query.edit_message_text("✅ *PDF successfully compressed!*", parse_mode="Markdown")
            if os.path.exists(output_compressed): os.remove(output_compressed)
        except Exception as e:
            logging.error(f"Error Compress PDF: {e}")
            await query.edit_message_text("❌ Failed to compress PDF.")

    elif action == "remove_pass":
        await query.edit_message_text("⏳ *Removing password protection...*", parse_mode="Markdown")
        output_unlocked = f"{os.path.splitext(input_path)[0]}_unlocked.pdf"
        try:
            reader = PdfReader(input_path)
            if reader.is_encrypted:
                reader.decrypt("")
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            with open(output_unlocked, "wb") as f:
                writer.write(f)
            with open(output_unlocked, 'rb') as pdf_file:
                await context.bot.send_document(chat_id=query.message.chat_id, document=pdf_file, filename=f"{os.path.splitext(file_name)[0]}_unlocked.pdf")
            await query.edit_message_text("✅ *PDF Password restrictions removed!*", parse_mode="Markdown")
            if os.path.exists(output_unlocked): os.remove(output_unlocked)
        except Exception as e:
            logging.error(f"Error Remove Pass: {e}")
            await query.edit_message_text("❌ Failed to unlock PDF.")

    elif action == "convert_image":
        await query.edit_message_text("⏳ *Exporting PDF pages as Images...*", parse_mode="Markdown")
        try:
            images = convert_from_path(input_path)
            for i, img in enumerate(images[:5]):
                img_path = f"page_{i+1}.png"
                img.save(img_path, 'PNG')
                with open(img_path, 'rb') as img_file:
                    await context.bot.send_photo(chat_id=query.message.chat_id, photo=img_file, caption=f"Page {i+1}")
                if os.path.exists(img_path): os.remove(img_path)
            await query.edit_message_text("✅ *PDF pages sent as Images!*", parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Error PDF to Image: {e}")
            await query.edit_message_text("❌ Failed to convert PDF to Images.")

    elif action == "img_to_pdf":
        await query.edit_message_text("⏳ *Converting Image to PDF...*", parse_mode="Markdown")
        output_pdf = f"{os.path.splitext(input_path)[0]}.pdf"
        try:
            image = Image.open(input_path)
            image_converted = image.convert('RGB')
            image_converted.save(output_pdf)
            with open(output_pdf, 'rb') as pdf_file:
                await context.bot.send_document(chat_id=query.message.chat_id, document=pdf_file, filename="converted_photo.pdf")
            await query.edit_message_text("✅ *Image successfully converted to PDF!*", parse_mode="Markdown")
            if os.path.exists(output_pdf): os.remove(output_pdf)
        except Exception as e:
            logging.error(f"Error Image to PDF: {e}")
            await query.edit_message_text("❌ Failed to convert Image to PDF.")

    if os.path.exists(input_path):
        os.remove(input_path)
    
    # ስራው ሲያልቅ የ user_data ማህደር ይጸዳል (እንደ አዲስ መጀመር አለበት)
    context.user_data.clear()

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
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("Bot is starting polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
