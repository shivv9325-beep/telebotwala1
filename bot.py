# bot.py

import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode, ChatAction

from config import BOT_TOKEN, ADMIN_IDS, TERABOX_DOMAINS
from extractors import extractor_manager
from utils import proxy_manager, cache_manager, rate_limiter

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ==================== MESSAGES ====================

WELCOME_MESSAGE = """
🎬 **Ultimate Terabox Video Downloader**

Welcome! I extract direct download links from Terabox.

✅ **Features:**
• Supports 40+ Terabox mirror sites
• Multiple extraction methods
• Fast & reliable
• Direct playable links

📋 **Usage:** Just send me any Terabox link!

⚡ **Commands:**
/start - Welcome message
/help - Detailed help
/domains - Supported sites
/stats - Bot statistics
"""

HELP_MESSAGE = """
📖 **Help Guide**

**Supported Link Formats:**
• `https://terabox.com/s/1xxxxxx`
• `https://1024tera.com/s/1xxxxxx`
• `https://teraboxapp.com/sharing/link?surl=xxxxx`
• And 40+ more domains!

**How it works:**
1. Send me a Terabox link
2. I try multiple extraction methods
3. You get direct download links!

**Tips:**
• Links must be public
• Download links expire in ~8 hours
• Video files marked with 🎬
"""


# ==================== HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    keyboard = [
        [
            InlineKeyboardButton("📖 Help", callback_data="help"),
            InlineKeyboardButton("🌐 Domains", callback_data="domains")
        ],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")]
    ]
    
    await update.message.reply_text(
        WELCOME_MESSAGE,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.MARKDOWN)


async def domains_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /domains command"""
    domains_list = sorted(TERABOX_DOMAINS)[:20]
    
    text = "🌐 **Supported Domains**\n\n"
    for domain in domains_list:
        text += f"• `{domain}`\n"
    text += f"\n...and {len(TERABOX_DOMAINS) - 20} more!"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    cache_stats = cache_manager.memory_cache.get_stats()
    proxy_stats = proxy_manager.get_stats()
    
    text = f"""
📊 **Bot Statistics**

**Cache:**
• Size: {cache_stats['size']}/{cache_stats['max_size']}
• Hit Rate: {cache_stats['hit_rate']}

**Proxies:**
• Active: {proxy_stats['alive']}/{proxy_stats['total']}

**Domains:** {len(TERABOX_DOMAINS)} supported
"""
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def process_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process Terabox links"""
    message = update.message
    url = message.text.strip()
    user_id = message.from_user.id
    
    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
    
    processing_msg = await message.reply_text(
        "⏳ **Processing your link...**\n\n"
        "🔍 Trying multiple extraction methods...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        result = await extractor_manager.extract(url, user_id)
        
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            await processing_msg.edit_text(
                f"❌ **Extraction Failed**\n\n"
                f"**Error:** {error}\n\n"
                f"The link might be private, expired, or deleted.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        files = result.get("files", [])
        
        if not files:
            await processing_msg.edit_text("❌ No files found in the link.")
            return
        
        await processing_msg.delete()
        
        for i, file_info in enumerate(files, 1):
            await send_file_result(message, file_info, i, len(files))
            if i < len(files):
                await asyncio.sleep(0.5)
    
    except Exception as e:
        logger.error(f"Error processing link: {e}")
        await processing_msg.edit_text(
            f"❌ **An error occurred**\n\nPlease try again later.",
            parse_mode=ParseMode.MARKDOWN
        )


async def send_file_result(message, file_info: dict, index: int, total: int):
    """Send formatted file result"""
    filename = file_info.get("filename", "Unknown")
    size = file_info.get("formatted_size", "Unknown")
    direct_link = file_info.get("direct_link", "")
    is_video = file_info.get("is_video", False)
    thumbnail = file_info.get("thumbnail", "")
    duration = file_info.get("duration", "")
    
    emoji = "🎬" if is_video else "📁"
    
    text = f"{emoji} **File {index}/{total}**\n\n"
    text += f"📄 **Name:** `{filename[:50]}{'...' if len(filename) > 50 else ''}`\n"
    text += f"📦 **Size:** {size}\n"
    
    if duration:
        text += f"⏱ **Duration:** {duration}\n"
    
    text += f"\n✅ **Status:** Ready to download"
    
    buttons = []
    if direct_link:
        buttons.append([
            InlineKeyboardButton("⬇️ Download", url=direct_link),
            InlineKeyboardButton("▶️ Stream", url=direct_link)
        ])
    
    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
    
    if thumbnail and is_video:
        try:
            await message.reply_photo(
                photo=thumbnail,
                caption=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
        except:
            pass
    
    await message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "help":
        await query.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.MARKDOWN)
    elif data == "domains":
        domains = sorted(TERABOX_DOMAINS)[:15]
        text = "🌐 **Top Domains:**\n\n" + "\n".join([f"• `{d}`" for d in domains])
        await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    elif data == "stats":
        stats = cache_manager.memory_cache.get_stats()
        await query.message.reply_text(f"📊 Cache hit rate: {stats['hit_rate']}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Error: {context.error}")


# ==================== INITIALIZATION ====================

async def post_init(application: Application):
    """Initialize after startup"""
    await proxy_manager.initialize()
    await cache_manager.initialize()
    
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Get help"),
        BotCommand("domains", "List supported domains"),
        BotCommand("stats", "View statistics"),
    ]
    await application.bot.set_my_commands(commands)
    
    logger.info("Bot initialized successfully!")


async def shutdown(application: Application):
    """Cleanup on shutdown"""
    await extractor_manager.close_all()
    logger.info("Bot shut down cleanly")


def main():
    """Start the bot"""
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(shutdown)
        .build()
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("domains", domains_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        process_link
    ))
    
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_error_handler(error_handler)
    
    logger.info("Starting Terabox Downloader Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
