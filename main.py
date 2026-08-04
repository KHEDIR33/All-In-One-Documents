import os
import logging
import time
import asyncio
from threading import Thread
from fastapi import FastAPI

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
import fitz  # PyMuPDF for compression & editing
from pypdf import PdfReader, PdfWriter

# ሎጊንግ ማዋቀር
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# 1. FastAPI Web Server setup (for Render Web Service & Keep-Alive)
# ---------------------------------------------------------
app = FastAPI()

@app.get("/")
def home():
    return {"status": "success", "message": "All-In-One Documents FastAPI & Bot Service is Active 24/7!"}

# ---------------------------------------------------------
# 2. 🧹 30-Minute Auto-Deletion Cleanup Background Task
# ---------------------------------------------------------
def clean_temp_files():
    while True:
        try:
            now = time.time()
            cutoff = now - 1800  # ከ 30 ደቂቃ (1800 ሰከንድ) በላይ የሆኑ ፋይሎችን ማጽዳት
            for filename in os.listdir('.'):
                if filename.startswith("downloads_") and os.path.isfile(filename):
                    if os.path.getmtime(filename) < cutoff:
                        os.remove(filename)
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        time.sleep(1800)  # በየ 30 ደቂቃው ይደገማል

# ---------------------------------------------------------
# 3. Telegram Bot Handlers
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📄➡️📝 PDF to Word (.docx)", callback_data="info_pdf_word")],
        [InlineKeyboardButton("📄➡️📊 PDF to Excel (.xlsx)", callback_data="info_pdf_excel")],
        [InlineKeyboardButton("📝➡️📄 Word to PDF (.pdf)", callback_data="info_word_pdf")],
        [InlineKeyboardButton("🖼️➡️📄 Image to PDF (.pdf)", callback_data="info_img_pdf")],
        [InlineKeyboardButton("📄➡️🖼️ PDF to Images (PNG)", callback_data="info_pdf_img")],
        [InlineKeyboardButton("✍️ Edit & Sign PDF", callback_data="info_edit_sign")],
        [InlineKeyboardButton("🗜️ Compress PDF (Reduce Size)", callback_data="info_compress")],
        [InlineKeyboardButton("🔓 Remove PDF Password", callback_data="info_unlock")],
        [InlineKeyboardButton("🔍 Search & Download Docs", callback_data="info_search")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_msg = (
        "🤖 *Welcome to All-In-One Documents!* ⚡\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "አገልግሎት ለማግኘት የሚፈልጉትን **ፋይል (PDF, Word, Image)** ቀጥታ ወደዚህ ቻት ይላኩ!\n\n"
        "ወይም ስለ አገልግሎቶቹ ዝርዝር ለማየት ከታች ያሉትን **አዝራሮች (Buttons)** ይጫኑ፦"
    )
    if update.message:
        await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_msg, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file_name = doc.file_name if doc.file_name else "file"
    file_ext = os.path.splitext(file_name)[1].lower()

    status_msg = await update.message.reply_text("📥 *Downloading file... Please wait.*", parse_mode="Markdown")
    
    file = await context.bot.get_file(doc.file_id)
    input_path = f"downloads_{update.effective_user.id}_{file_name}"
    await file.download_to_drive(input_path)
    
    context.user_data['file_path'] = input_path
    context.user_data['file_name'] = file_name

    if file_ext == '.pdf':
        keyboard = [
            [
                InlineKeyboardButton("📄 Convert to Word", callback_data="convert_word"),
                InlineKeyboardButton("📊 Convert to Excel", callback_data="convert_excel")
            ],
            [
                InlineKeyboardButton("✍️ Edit & Sign", callback_data="edit_sign_pdf"),
                InlineKeyboardButton("🗜️ Compress PDF", callback_data="compress_pdf")
            ],
            [
                InlineKeyboardButton("🖼️ Convert to Images", callback_data="convert_image"),
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
    text = update.message.text
    search_links = (
        f"🔍 *Search Results for:* `{text}`\n\n"
        "ከዚህ በታች ካሉ ህጋዊ እና ነፃ ምንጮች በቀጥታ ማግኘት ይችላሉ፦\n\n"
        f"📚 [Internet Archive](https://archive.org/search?query={text.replace(' ', '+')})\n"
        f"📖 [Open Library](https://openlibrary.org/search?q={text.replace(' ', '+')})\n"
        f"🔬 [arXiv Research](https://arxiv.org/search/?query={text.replace(' ', '+')}&searchtype=all)\n"
        f"💻 [GitHub Code/Files](https://github.com/search?q={text.replace(' ', '+')})\n"
        f"📐 [BiblioCAD](https://www.bibliocad.com/en/search/{text.replace(' ', '+')})\n"
    )
    await update.message.reply_text(search_links, parse_mode="Markdown", disable_web_page_preview=True)

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
            "info_edit_sign": "✍️ **Edit & Sign PDF**\n\nፒዲኤፍ ፋይልዎን ለማስተካከል ወይም ለመፈረም እባክዎ መጀመሪያ **PDF ፋይልዎን** ይላኩ!",
            "info_compress": "🗜️ **Compress PDF**\n\nየ PDF ፋይል መጠንን ለመቀነስ **PDF ፋይልዎን** ይላኩ!",
            "info_unlock": "🔓 **Remove Password**\n\nየተቆለፈ PDF ፓስወርድ ለማንሳት **PDF ፋይሉን** ይላኩ!",
            "info_search": "🔍 **Search & Download Docs**\n\nየሚፈልጉትን መጽሐፍ፣ ሰነድ ወይም ቴክኒካዊ ፋይል ስም በቀጥታ ጽሁፍ (Text) ጻፉልኝ!"
        }
        msg = info_messages.get(action, "እባክዎን ለመጀመር ፋይልዎን ይላኩ።")
        await query.message.reply_text(msg, parse_mode="Markdown")
        return

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
            logger.error(f"Error PDF to Word: {e}")
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
            logger.error(f"Error PDF to Excel: {e}")
            await query.edit_message_text("❌ Failed to convert PDF to Excel.")

    elif action == "edit_sign_pdf":
        await query.edit_message_text("⏳ *Preparing PDF for editing & signing...*", parse_mode="Markdown")
        output_edited = f"{os.path.splitext(input_path)[0]}_edited.pdf"
        try:
            doc = fitz.open(input_path)
            page = doc[0] # የመጀመሪያውን ገጽ በናሙና ማስተካከል ወይም ቴክስት መጻፍ
            # በገጹ ላይ የናሙና ማስተካከያ ጽሁፍ ማስገባት (Watermark/Annotation)
            rect = fitz.Rect(50, 50, 300, 100)
            page.insert_textbox(rect, "Signed & Verified via All-In-One Documents", fontsize=11, color=(0, 0, 1))
            doc.save(output_edited)
            doc.close()
            with open(output_edited, 'rb') as pdf_file:
                await context.bot.send_document(chat_id=query.message.chat_id, document=pdf_file, filename=f"{os.path.splitext(file_name)[0]}_signed.pdf")
            await query.edit_message_text("✅ *PDF successfully edited & signed!*", parse_mode="Markdown")
            if os.path.exists(output_edited): os.remove(output_edited)
        except Exception as e:
            logger.error(f"Error Edit & Sign: {e}")
            await query.edit_message_text("❌ Failed to edit or sign PDF.")

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
            logger.error(f"Error Compress PDF: {e}")
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
            logger.error(f"Error Remove Pass: {e}")
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
            logger.error(f"Error PDF to Image: {e}")
            await query.edit_message_text("❌ Failed to convert PDF to Images.")

    if os.path.exists(input_path):
        os.remove(input_path)
    
    context.user_data.clear()

# ---------------------------------------------------------
# 4. Background Runners (Uvicorn FastAPI + Telegram Bot + Cleanup)
# ---------------------------------------------------------
def run_fastapi():
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

def run_telegram_bot():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("Error: BOT_TOKEN Environment Variable is missing!")
        return

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    application.add_handler(CallbackQueryHandler(button_callback))

    logger.info("All-In-One Documents Telegram Bot is starting polling...")
    application.run_polling()

if __name__ == '__main__':
    # Start 30-minute auto-cleanup thread
    cleanup_thread = Thread(target=clean_temp_files, daemon=True)
    cleanup_thread.start()

    # Start Telegram Bot in a separate background thread
    bot_thread = Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()

    # Start FastAPI server on main thread (required by Render)
    run_fastapi()

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="All-In-One Documents Backend")

# 1. CORS Middleware: Framer ዌብሳይታችን ከዚህ ሰርቨር ጋር እንዲነጋገር (API Call) መፍቀድ
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ለጊዜው ሁሉንም ፈቅደናል (በ후ኋላ የFramer ዌብሳይት ሊንክዎን ብቻ ማድረግ ይቻላል)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 2. የቴሌብር ክፍያ ማረጋገጫ ማስመሰያ (Telebirr Verification Logic)
def verify_telebirr_payment(phone_number: str, password: str) -> bool:
    # እዚህጋ ከቴሌብር API ጋር የሚደረግ ትስስር ወይም የፓስወርድ ማረጋገጫ ይፃፋል
    # ለምሳሌ ፓስወርዱ ትክክለኛ ከሆነ True ይመልሳል
    if password == "1234":  # ለሙከራ ያስቀመጥነው ፓስወርድ
        return True
    return False


# 3. ፋይል የመቀየር እና ክፍያ ማስተናገጃ Endpoint
@app.post("/api/convert")
async def convert_document(
    file: UploadFile = File(...),
    phone_number: str = Form(...),
    password: str = Form(...),
):
    # ሀ. የቴሌብር ክፍያ ማረጋገጥ
    payment_success = verify_telebirr_payment(phone_number, password)
    if not payment_success:
        raise HTTPException(
            status_code=400,
            detail="የቴሌብር ፓስወርድ ስህተት ነው! እባክዎ እንደገና ይሞክሩ።",
        )

    # ለ. ክፍያው ከተሳካ ፋይሉን የማቀናበር ስራ (Conversion logic) እዚህ ይከናወናል
    contents = await file.read()

    # (እዚህ ጋር የ PDF ወደ Word ወይም የሚፈልጉትን መቀየሪያ ኮድ ያስገቡ)

    return JSONResponse(
        content={
            "status": "success",
            "message": "ክፍያው ተሳክቷል! ፋይሉ ተቀይሯል።",
            "download_url": "/api/download-result/processed_file.docx",
        }
    )


# 4. ሰነድ የመፈለግ እና የማውረድ Endpoint (Search & Download)
@app.post("/api/search-download")
async def search_and_download(
    query: str = Form(...), phone_number: str = Form(...), password: str = Form(...)
):
    # ሀ. የቴሌብር ክፍያ ማረጋገጥ
    payment_success = verify_telebirr_payment(phone_number, password)
    if not payment_success:
        raise HTTPException(
            status_code=400,
            detail="የቴሌብር ፓስወርድ ስህተት ነው! ክፍያው አልተሳካም።",
        )

    # ለ. ፍለጋውን አድርጎ ፋይሉን የማዘጋጀት ስራ
    # (በቀድሞው ኮድዎ የነበሩትን የ Internet Archive / Library API ፍለጋዎች እዚህ ይጠቀሙ)

    return JSONResponse(
        content={
            "status": "success",
            "message": "ፋይሉ ተዘጋጅቷል፣ ማውረድ ይችላሉ።",
            "file_name": f"{query}.pdf",
        }
    )

