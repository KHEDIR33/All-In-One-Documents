const express = require('express');
const cors = require('cors');
require('dotenv').config();
const { Telegraf } = require('telegraf');

const app = express();
app.use(express.json());
app.use(cors());

// 1. የጤና ማረጋገጫ (Health Check for Render)
app.get('/', (req, res) => {
    res.json({ success: true, message: 'All-In-One Documents Node.js & Bot Service is Active 24/7! 🚀' });
});

// 2. የክፍያ እና ፋይል ማቀናበሪያ API (Chapa, Santim Pay, Telebirr)
app.post('/api/convert', async (req, res) => {
    try {
        const { gateway, phoneNumber, password, fileName } = req.body;

        if (password !== "1234") {
            return res.status(400).json({ success: false, message: 'የክፍያ ፓስወርድ ስህተት ነው!' });
        }

        res.json({
            success: true,
            message: 'ክፍያው ተሳክቷል! ፋይሉ ተቀይሯል።',
            download_url: `/api/download-result/processed_${fileName || 'file.docx'}`
        });

    } catch (error) {
        console.error(error);
        res.status(500).json({ success: false, message: 'የሰርቨር ስህተት አጋጥሟል', error: error.message });
    }
});

// 3. Telegram Bot Setup (Telegraf)
const token = process.env.BOT_TOKEN;
if (!token) {
    console.error("Error: BOT_TOKEN Environment Variable is missing!");
} else {
    const bot = new Telegraf(token);

    bot.start((ctx) => {
        ctx.reply(
            "🤖 *Welcome to All-In-One Documents!* ⚡\n\nአገልግሎት ለማግኘት የሚፈልጉትን ፋይል (PDF, Word, Image) ቀጥታ ወደዚህ ቻት ይላኩ!",
            { parse_mode: 'Markdown' }
        );
    });

    bot.on('text', (ctx) => {
        const text = ctx.message.text;
        ctx.reply(
            `🔍 *Search Results for:* \`${text}\`\n\n📚 [Internet Archive](https://archive.org/search?query=${encodeURIComponent(text)})`,
            { parse_mode: 'Markdown' }
        );
    });

    bot.launch();
    console.log("Telegram Bot is running...");

    process.once('SIGINT', () => bot.stop('SIGINT'));
    process.once('SIGTERM', () => bot.stop('SIGTERM'));
}

// 4. ሰርቨሩን ማስጀመር
const PORT = process.env.PORT || 10000;
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});
