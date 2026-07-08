import os
import sys
import logging
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from deep_translator import GoogleTranslator

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Environment variables
TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    logger.error("TELEGRAM_TOKEN environment variable not set!")
    sys.exit(1)

ENVIRONMENT = os.environ.get('ENVIRONMENT', 'production')

# Language database
LANGUAGES: Dict[str, str] = {
    'en': 'English', 'hi': 'Hindi', 'es': 'Spanish', 'fr': 'French',
    'de': 'German', 'zh': 'Chinese', 'ar': 'Arabic', 'ja': 'Japanese',
    'ko': 'Korean', 'ru': 'Russian', 'pt': 'Portuguese', 'it': 'Italian',
    'nl': 'Dutch', 'bn': 'Bengali', 'ta': 'Tamil', 'te': 'Telugu',
    'ur': 'Urdu', 'pa': 'Punjabi', 'mr': 'Marathi', 'gu': 'Gujarati',
    'kn': 'Kannada', 'ml': 'Malayalam', 'tr': 'Turkish', 'vi': 'Vietnamese',
    'th': 'Thai', 'id': 'Indonesian', 'pl': 'Polish', 'uk': 'Ukrainian',
    'ro': 'Romanian', 'el': 'Greek', 'he': 'Hebrew', 'sv': 'Swedish',
    'da': 'Danish', 'fi': 'Finnish', 'no': 'Norwegian', 'cs': 'Czech'
}

# User preferences storage
user_preferences: Dict[int, str] = {}
user_history: Dict[int, list] = {}

# Initialize translator
translator = GoogleTranslator()

def create_main_keyboard() -> InlineKeyboardMarkup:
    """Create main keyboard with buttons."""
    keyboard = [
        [
            InlineKeyboardButton("🌍 Change Language", callback_data='change_lang'),
            InlineKeyboardButton("📝 History", callback_data='show_history')
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data='show_help'),
            InlineKeyboardButton("ℹ️ About", callback_data='show_about')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_language_keyboard() -> InlineKeyboardMarkup:
    """Create language selection keyboard."""
    lang_buttons = []
    row = []
    
    sorted_langs = sorted(LANGUAGES.items(), key=lambda x: x[1])
    
    for i, (code, name) in enumerate(sorted_langs, 1):
        row.append(InlineKeyboardButton(name, callback_data=f'set_lang_{code}'))
        if len(row) == 3:
            lang_buttons.append(row)
            row = []
    
    if row:
        lang_buttons.append(row)
    
    lang_buttons.append([
        InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')
    ])
    
    return InlineKeyboardMarkup(lang_buttons)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    welcome_message = f"""
🌟 **Welcome {user.first_name}!** 

I'm your Language Translator Bot powered by Google Translate.

**✨ Features:**
• Translate between 35+ languages
• Auto-detect source language
• Smart language preferences
• Translation history
• Clean button-based interface

**📌 Quick Commands:**
• `/help` - Show all commands
• `/language [code]` - Set preferred language
• `/languages` - List all supported languages
• `/translate [code] [text]` - Translate specific text

**💡 Try it now!** 
Send me any text and watch it translate instantly! 🚀
"""
    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown',
        reply_markup=create_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = """
🤖 **Language Translator Bot - Help Guide**

**📋 Available Commands:**
• `/start` - Welcome message
• `/help` - Display this help
• `/languages` - List all languages
• `/language [code]` - Set preferred language
• `/translate [code] [text]` - Translate specific text

**🔍 How to Use:**
1. **Auto-translate:** Just send me any text
2. **Set Language:** `/language es` for Spanish
3. **Specific Translation:** `/translate fr Hello world`

**🌍 Popular Language Codes:**
`en`-English, `es`-Spanish, `fr`-French, `de`-German
`hi`-Hindi, `zh`-Chinese, `ar`-Arabic, `ja`-Japanese

**⭐ Tips:**
• Use buttons for easier navigation
• Your language preference is saved
• View your translation history
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def languages_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /languages command."""
    lang_list = "\n".join([f"• `{code}` - {name}" for code, name in sorted(LANGUAGES.items(), key=lambda x: x[1])])
    message = f"""
🌍 **Supported Languages ({len(LANGUAGES)})**

{lang_list}

**Set your preferred language:**
`/language [code]`
Example: `/language fr`
"""
    await update.message.reply_text(message, parse_mode='Markdown')

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /language command."""
    try:
        args = context.args
        if not args:
            await update.message.reply_text(
                "⚠️ Please provide a language code.\n"
                "Usage: `/language [code]`\n"
                "Example: `/language es`\n\n"
                "Use `/languages` to see all available codes.",
                parse_mode='Markdown'
            )
            return
        
        lang_code = args[0].lower()
        user_id = update.effective_user.id
        
        if lang_code in LANGUAGES:
            user_preferences[user_id] = lang_code
            await update.message.reply_text(
                f"✅ **Language set to {LANGUAGES[lang_code]}!**\n\n"
                f"All future messages will be translated to {LANGUAGES[lang_code]}.\n"
                f"Send me any text to test it out! 🚀",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ Language '{lang_code}' not supported.\n"
                f"Use `/languages` to see all available codes.",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Language command error: {e}")
        await update.message.reply_text("❌ Failed to set language. Please try again.")

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /translate command."""
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "⚠️ **Usage:** `/translate [language_code] [text]`\n\n"
                "Example: `/translate es Hello world`\n"
                "This will translate 'Hello world' to Spanish.",
                parse_mode='Markdown'
            )
            return
        
        target_lang = args[0].lower()
        text_to_translate = ' '.join(args[1:])
        
        if target_lang not in LANGUAGES:
            await update.message.reply_text(
                f"❌ Language '{target_lang}' not supported.\n"
                f"Use `/languages` to see all available codes.",
                parse_mode='Markdown'
            )
            return
        
        translated = GoogleTranslator(source='auto', target=target_lang).translate(text_to_translate)
        
        response = f"""
✅ **Translation to {LANGUAGES[target_lang]}**

📝 **Original:** {text_to_translate}
🌐 **Translated:** {translated}
"""
        await update.message.reply_text(response, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Translate command error: {e}")
        await update.message.reply_text("❌ Translation failed. Please try again.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages."""
    try:
        text = update.message.text
        user_id = update.effective_user.id
        
        if text.startswith('/'):
            return
        
        await update.message.chat.send_action(action="typing")
        
        target_lang = user_preferences.get(user_id, 'en')
        
        translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
        
        if not translated:
            await update.message.reply_text(
                "❌ Sorry, I couldn't translate that. Please try again."
            )
            return
        
        response = f"""
✅ **Translation**

📝 **Original:** {text}
🌐 **Translated ({LANGUAGES[target_lang]}):** {translated}
"""
        
        await update.message.reply_text(
            response,
            parse_mode='Markdown',
            reply_markup=create_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Message handling error: {e}")
        await update.message.reply_text(
            "⚠️ An error occurred. Please try again."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == 'change_lang':
            await query.edit_message_text(
                "🌍 **Select your preferred language:**\n\n"
                "Choose a language for all future translations:",
                parse_mode='Markdown',
                reply_markup=create_language_keyboard()
            )
        
        elif query.data.startswith('set_lang_'):
            lang_code = query.data.replace('set_lang_', '')
            user_id = update.effective_user.id
            user_preferences[user_id] = lang_code
            
            await query.edit_message_text(
                f"✅ **Language set to {LANGUAGES[lang_code]}!**\n\n"
                f"Now I'll translate everything to {LANGUAGES[lang_code]}.\n"
                f"Send me any text to try it out! 🚀",
                parse_mode='Markdown',
                reply_markup=create_main_keyboard()
            )
        
        elif query.data == 'show_history':
            user_id = update.effective_user.id
            history = user_history.get(user_id, [])
            
            if not history:
                await query.edit_message_text(
                    "📝 **No translation history yet!**\n\n"
                    "Start translating some text and it will appear here.",
                    parse_mode='Markdown',
                    reply_markup=create_main_keyboard()
                )
                return
            
            recent = history[-5:][::-1]
            history_text = "\n\n".join([
                f"**{i+1}.** {entry['original'][:50]}...\n"
                f"➜ {entry['translated'][:50]}..."
                for i, entry in enumerate(recent)
            ])
            
            await query.edit_message_text(
                f"📝 **Your Recent Translations ({len(history)} total)**\n\n{history_text}\n\n"
                f"💡 Send more text to build your history!",
                parse_mode='Markdown',
                reply_markup=create_main_keyboard()
            )
        
        elif query.data == 'show_help':
            help_text = """
📋 **Quick Commands:**
• `/start` - Welcome
• `/help` - Help guide
• `/languages` - All languages
• `/language [code]` - Set preference
• `/translate [code] [text]` - Translate

💡 **Try:** Send any text for instant translation!
"""
            await query.edit_message_text(
                help_text,
                parse_mode='Markdown',
                reply_markup=create_main_keyboard()
            )
        
        elif query.data == 'show_about':
            about_text = """
🤖 **Language Translator Bot**

**Version:** 2.0.0
**Powered by:** Google Translate API
**Built with:** Python + python-telegram-bot
**Hosted on:** Railway

**Features:**
• 35+ languages
• Auto-detection
• Smart preferences
• Translation history
• Button-based interface
"""
            await query.edit_message_text(
                about_text,
                parse_mode='Markdown',
                reply_markup=create_main_keyboard()
            )
        
        elif query.data == 'back_to_main':
            await query.edit_message_text(
                "🏠 **Back to Main Menu**\n\n"
                "Send me any text to translate, or use the buttons below!",
                parse_mode='Markdown',
                reply_markup=create_main_keyboard()
            )
    
    except Exception as e:
        logger.error(f"Callback handler error: {e}")
        await query.edit_message_text(
            "❌ An error occurred. Please try again.",
            reply_markup=create_main_keyboard()
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors gracefully."""
    logger.error(f"Update {update} caused error: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An unexpected error occurred. Please try again later."
        )

def main() -> None:
    """Start the bot."""
    logger.info("Starting Language Translator Bot...")
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Bot token: {'*' * 10}{TOKEN[-4:]}")
    
    # Build application with new version
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('languages', languages_command))
    application.add_handler(CommandHandler('language', language_command))
    application.add_handler(CommandHandler('translate', translate_command))
    
    # Add message handler
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Starting bot with long polling...")
    application.run_polling()
    
    logger.info("Bot stopped.")

if __name__ == '__main__':
    main()
