import os
import sys
import logging
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from deep_translator import GoogleTranslator
from datetime import datetime

# Configure logging for Railway
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Environment variables
TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    logger.error("TELEGRAM_TOKEN environment variable not set!")
    sys.exit(1)

PORT = int(os.environ.get('PORT', 8443))
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'production')

# Language database
LANGUAGES: Dict[str, str] = {
    'en': 'English',
    'hi': 'Hindi',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'zh': 'Chinese (Simplified)',
    'zh-TW': 'Chinese (Traditional)',
    'ar': 'Arabic',
    'ja': 'Japanese',
    'ko': 'Korean',
    'ru': 'Russian',
    'pt': 'Portuguese',
    'it': 'Italian',
    'nl': 'Dutch',
    'bn': 'Bengali',
    'ta': 'Tamil',
    'te': 'Telugu',
    'ur': 'Urdu',
    'pa': 'Punjabi',
    'mr': 'Marathi',
    'gu': 'Gujarati',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'tr': 'Turkish',
    'vi': 'Vietnamese',
    'th': 'Thai',
    'id': 'Indonesian',
    'pl': 'Polish',
    'uk': 'Ukrainian',
    'ro': 'Romanian'
}

# User preferences storage (in-memory - for production use Redis/PostgreSQL)
user_preferences: Dict[int, str] = {}
user_history: Dict[int, list] = {}

# Initialize translator
translator = GoogleTranslator()

# ==================== Helper Functions ====================

def get_language_name(lang_code: str) -> str:
    """Get language name from code."""
    return LANGUAGES.get(lang_code, lang_code)

def detect_language(text: str) -> str:
    """Detect language of text."""
    try:
        return translator.detect(text)
    except:
        return 'en'

def translate_text(text: str, target_lang: str = 'en') -> Optional[str]:
    """Translate text to target language."""
    try:
        source_lang = detect_language(text)
        if source_lang == target_lang:
            return text
        translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
        return translated
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return None

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
    """Create language selection keyboard with pagination."""
    lang_buttons = []
    row = []
    
    # Sort languages alphabetically
    sorted_langs = sorted(LANGUAGES.items(), key=lambda x: x[1])
    
    for i, (code, name) in enumerate(sorted_langs, 1):
        row.append(InlineKeyboardButton(name, callback_data=f'set_lang_{code}'))
        if len(row) == 3:  # 3 buttons per row for better mobile view
            lang_buttons.append(row)
            row = []
    
    if row:
        lang_buttons.append(row)
    
    # Add navigation buttons
    lang_buttons.append([
        InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')
    ])
    
    return InlineKeyboardMarkup(lang_buttons)

# ==================== Command Handlers ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    welcome_message = f"""
🌟 **Welcome {user.first_name}!** 

I'm your advanced Language Translator Bot powered by Google Translate.

**✨ Features:**
• Translate between 30+ languages
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
    
    keyboard = create_main_keyboard()
    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = """
🤖 **Language Translator Bot - Help Guide**

**📋 Available Commands:**
• `/start` - Show welcome message
• `/help` - Display this help guide
• `/languages` - List all supported languages
• `/language [code]` - Set your preferred language
• `/translate [code] [text]` - Translate specific text

**🔍 How to Use:**
1. **Auto-translate:** Just send me any text
2. **Set Language:** Use `/language es` for Spanish
3. **Specific Translation:** `/translate fr Hello world`

**🌍 Language Codes:**
`en`-English, `es`-Spanish, `fr`-French, `de`-German
`hi`-Hindi, `zh`-Chinese, `ar`-Arabic, `ja`-Japanese

**⭐ Tips:**
• Use buttons for easier navigation
• Your language preference is saved
• View your translation history

Need more help? Visit our GitHub repository!
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
        
        translated = translate_text(text_to_translate, target_lang)
        if translated:
            response = f"""
✅ **Translation to {LANGUAGES[target_lang]}**

📝 **Original:** {text_to_translate}
🌐 **Translated:** {translated}
"""
            await update.message.reply_text(response, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Translation failed. Please try again.")
            
    except Exception as e:
        logger.error(f"Translate command error: {e}")
        await update.message.reply_text("❌ Translation failed. Please try again.")

# ==================== Message Handler ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages."""
    try:
        text = update.message.text
        user_id = update.effective_user.id
        
        # Skip commands
        if text.startswith('/'):
            return
        
        # Send typing indicator
        await update.message.chat.send_action(action="typing")
        
        # Get user's preferred language
        target_lang = user_preferences.get(user_id, 'en')
        
        # Detect source language
        source_lang = detect_language(text)
        source_lang_name = get_language_name(source_lang)
        
        # Translate
        translated = translate_text(text, target_lang)
        
        if not translated:
            await update.message.reply_text(
                "❌ Sorry, I couldn't translate that. Please try again with shorter text."
            )
            return
        
        # Save to history
        if user_id not in user_history:
            user_history[user_id] = []
        user_history[user_id].append({
            'original': text,
            'translated': translated,
            'source_lang': source_lang,
            'target_lang': target_lang,
            'timestamp': datetime.now().isoformat()
        })
        # Keep only last 50 entries
        if len(user_history[user_id]) > 50:
            user_history[user_id] = user_history[user_id][-50:]
        
        # Prepare response
        if source_lang == target_lang:
            response = f"""
ℹ️ **Text already in {LANGUAGES[target_lang]}**

📝 **Message:** {text}

💡 To translate to another language, use:
`/language [code]` to change your preference
`/translate [code] [text]` for specific translations
"""
        else:
            response = f"""
✅ **Translation Complete**

📝 **Original ({source_lang_name}):** {text}
🌐 **Translated ({LANGUAGES[target_lang]}):** {translated}
"""
        
        keyboard = create_main_keyboard()
        await update.message.reply_text(
            response,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Message handling error: {e}")
        await update.message.reply_text(
            "⚠️ An error occurred while processing your message. Please try again."
        )

# ==================== Callback Query Handler ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == 'change_lang':
            keyboard = create_language_keyboard()
            await query.edit_message_text(
                "🌍 **Select your preferred language:**\n\n"
                "Choose a language for all future translations:",
                parse_mode='Markdown',
                reply_markup=keyboard
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
            
            # Show last 5 translations
            recent = history[-5:][::-1]  # Reverse to show latest first
            history_text = "\n\n".join([
                f"**{i+1}.** {entry['original'][:50]}...\n"
                f"➜ {entry['translated'][:50]}...\n"
                f"_From {get_language_name(entry['source_lang'])} to {get_language_name(entry['target_lang'])}_"
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
• 30+ languages
• Auto-detection
• Smart preferences
• Translation history
• Button-based interface

**Source Code:** GitHub
**Developer:** @yourusername
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

# ==================== Error Handler ====================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors gracefully."""
    logger.error(f"Update {update} caused error: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An unexpected error occurred. Please try again later."
        )

# ==================== Main Function ====================

def main() -> None:
    """Start the bot."""
    logger.info("Starting Language Translator Bot...")
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Bot token: {'*' * 10}{TOKEN[-4:]}")
    
    # Build application
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('languages', languages_command))
    application.add_handler(CommandHandler('language', language_command))
    application.add_handler(CommandHandler('translate', translate_command))
    
    # Add message handler for text messages
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    if ENVIRONMENT == 'production':
        logger.info("Starting bot in production mode...")
        application.run_polling()
    else:
        logger.info("Starting bot in development mode...")
        application.run_polling()
    
    logger.info("Bot stopped.")

if __name__ == '__main__':
    main()
