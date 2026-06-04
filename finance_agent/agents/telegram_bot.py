import asyncio
import time
from pathlib import Path
from telegram import Bot, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes
from utils.config import Config
from utils.logger import get_logger

# Initialize module logger
logger = get_logger("telegram_bot")

class TelegramApprovalBot:
    """
    Agent responsible for sending carousel slide previews to the user via Telegram
    and waiting for interactive approval before publishing to Instagram.
    """
    
    def __init__(self):
        """
        Initializes the Telegram Bot.
        """
        # Validate that Telegram credentials are provided in .env
        if not Config.TELEGRAM_BOT_TOKEN or "your_" in Config.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is missing or contains placeholder values in .env")
        if not Config.TELEGRAM_CHAT_ID or "your_" in Config.TELEGRAM_CHAT_ID:
            raise ValueError("TELEGRAM_CHAT_ID is missing or contains placeholder values in .env")
            
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        
        # State variable to track user approval response
        self.approval_result = None

    async def send_preview_and_wait(self, image_paths: list[str], timeout_minutes: int = 10) -> bool:
        """
        Sends the slide images as a swipeable media group gallery, sends an approval message
        with inline buttons, starts a temporary polling session, and blocks until the user replies.
        
        Telegram limits:
        - Media groups are limited to a maximum of 10 items (we send exactly 7 slides).
        - Direct message rate limit: 20 messages per minute to the same chat.
        
        Args:
            image_paths: List of absolute file paths to slide PNGs.
            timeout_minutes: Maximum duration to wait for user input before auto-rejecting.
        Returns:
            True if user clicked 'Approve', False if rejected or timed out.
        """
        logger.info(f"Preparing Telegram preview for Chat ID: {self.chat_id}")
        
        # 1. Build the telegram application instance
        application = ApplicationBuilder().token(self.bot_token).build()
        
        # Reset approval state
        self.approval_result = None
        
        # 2. Callback handler function for button interactions
        async def handle_approval_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()
            
            # Extract name of user who clicked
            user_name = query.from_user.first_name or "Someone"
            
            if query.data == "approve":
                self.approval_result = True
                logger.info(f"User {user_name} clicked: APPROVE & POST")
                await query.edit_message_text(text=f"✅ **Approved by {user_name}!** Auto-publishing carousel to Instagram now...")
            elif query.data == "reject":
                self.approval_result = False
                logger.info(f"User {user_name} clicked: REJECT & CANCEL")
                await query.edit_message_text(text=f"❌ **Rejected by {user_name}.** The publishing flow has been cancelled.")

        # Register callback query handler
        application.add_handler(CallbackQueryHandler(handle_approval_click))
        
        try:
            # 3. Start the bot and active polling in the background
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
            logger.info("Temporary Telegram polling bot started.")
            
            # 4. Prepare and send the swipeable image gallery (Media Group)
            media_group = []
            opened_files = [] # Track open files to close them safely later
            
            for path_str in image_paths:
                p = Path(path_str)
                if p.exists():
                    f = open(p, "rb")
                    opened_files.append(f)
                    media_group.append(InputMediaPhoto(media=f))
                else:
                    logger.warning(f"Slide file not found for Telegram preview: {path_str}")
                    
            if not media_group:
                logger.error("No valid slide images found to send to Telegram.")
                return False
                
            logger.info("Sending slide media group...")
            await application.bot.send_media_group(
                chat_id=self.chat_id,
                media=media_group,
                write_timeout=60,
                read_timeout=60
            )
            
            # Close all file streams safely
            for f in opened_files:
                f.close()
                
            # 5. Send message with inline keyboard action buttons
            keyboard = [
                [
                    InlineKeyboardButton("Approve & Post 🚀", callback_data="approve"),
                    InlineKeyboardButton("Reject & Cancel ❌", callback_data="reject")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            logger.info("Sending interactive approval message...")
            await application.bot.send_message(
                chat_id=self.chat_id,
                text="🤖 **Daily Finance Carousel is ready!**\nSwipe through the slide previews above and choose an action below:",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
            # 6. Poll status until user selects an action or timeout expires
            timeout_seconds = timeout_minutes * 60
            start_time = time.time()
            
            logger.info(f"Waiting up to {timeout_minutes} minutes for your response...")
            while self.approval_result is None:
                await asyncio.sleep(1.0)
                
                # Check for timeout
                if time.time() - start_time > timeout_seconds:
                    logger.warning("Telegram approval flow timed out.")
                    await application.bot.send_message(
                        chat_id=self.chat_id,
                        text="⏳ **Flow Timed Out.** Your daily carousel was auto-rejected because no response was received."
                    )
                    self.approval_result = False
                    break
                    
        except Exception as e:
            logger.error(f"Error during Telegram approval flow: {str(e)}")
            self.approval_result = False
        finally:
            # 7. Gracefully shut down the bot instance to free port/polling channels
            logger.info("Shutting down temporary polling bot...")
            if application.updater:
                await application.updater.stop()
            await application.stop()
            await application.shutdown()
            
        return self.approval_result

# Entry point for testing the bot standalone
if __name__ == "__main__":
    print("--- Telegram Approval Bot Agent Test ---")
    
    # Locate output directory and find generated slide images from Step 5
    out_dir = Path(__file__).resolve().parent.parent / "output"
    slides = sorted(list(out_dir.glob("slide_*.png")))
    slide_paths = [str(s) for s in slides]
    
    if not slide_paths:
        print("Error: No slide images found in output folder. Please run Step 5 canva_builder first.")
    else:
        print(f"Found {len(slide_paths)} slide images for preview.")
        bot = TelegramApprovalBot()
        
        # Execute async method inside sync wrapper
        approved = asyncio.run(bot.send_preview_and_wait(slide_paths, timeout_minutes=2))
        print(f"\nFinal Approval Decision: {'APPROVED' if approved else 'REJECTED'}")
