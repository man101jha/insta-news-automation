import os
import sys
import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

# Try to import logger and config
try:
    from upsc_agent.utils.logger import logger
    from upsc_agent.utils.config import config
except ImportError:
    # Fallback to local import if run directly
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.logger import logger
    from utils.config import config

class TelegramApprovalBot:
    def __init__(self):
        # Read tokens from configuration
        self.token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.result = None  # None = waiting, True = Approved, False = Rejected/Timed out
        self.approver_name = None

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Callback handler that processes user clicks on inline buttons."""
        query = update.callback_query
        await query.answer()

        # Check which button was clicked
        if query.data == "approve":
            self.result = True
            self.approver_name = query.from_user.first_name if query.from_user else "Admin"
            logger.info("Content APPROVED by %s", self.approver_name)
            
            # Edit caption to reflect approval status and remove inline keyboard buttons
            new_caption = query.message.caption + f"\n\n✅ Approved by {self.approver_name}"
            await query.edit_message_caption(caption=new_caption, reply_markup=None)
            
        elif query.data == "reject":
            self.result = False
            self.approver_name = query.from_user.first_name if query.from_user else "Admin"
            logger.info("Content REJECTED by %s", self.approver_name)
            
            # Edit caption to reflect rejection status and remove buttons
            new_caption = query.message.caption + f"\n\n❌ Rejected by {self.approver_name}"
            await query.edit_message_caption(caption=new_caption, reply_markup=None)

    async def timeout_handler(self, application: Application, message_id: int):
        """Monitors the approval window and triggers timeout after 30 minutes (1800s)."""
        # Timeout wait window
        timeout_seconds = 1800
        await asyncio.sleep(timeout_seconds)
        
        if self.result is None:
            logger.warning("Telegram approval window timed out.")
            self.result = False
            
            # Try to edit caption to reflect timeout and strip buttons
            try:
                bot = Bot(self.token)
                # Fetch existing message to update caption
                await bot.edit_message_caption(
                    chat_id=self.chat_id,
                    message_id=message_id,
                    caption="📚 UPSC MCQ Carousel Ready\n\n⚠️ Timed Out (No action taken)",
                    reply_markup=None
                )
            except Exception as e:
                logger.error("Failed to update message caption on timeout: %s", str(e))

    async def send_for_approval_async(self, photo_path: str, slide_data: dict) -> bool:
        """
        Sends the cover slide image and buttons to Telegram.
        Blocks until the user clicks Approve/Reject or the timeout is reached.
        """
        try:
            bot = Bot(token=self.token)
            
            # Extract statistics for metadata caption
            topics_list = ", ".join(slide_data.get("topics", []))
            mcqs = slide_data.get("mcqs", [])
            
            easy_count = sum(1 for m in mcqs if m.get("difficulty") == "Easy")
            medium_count = sum(1 for m in mcqs if m.get("difficulty") == "Medium")
            hard_count = sum(1 for m in mcqs if m.get("difficulty") == "Hard")

            caption = (
                f"📚 *UPSC MCQ Carousel Ready* — {slide_data.get('date', 'Today')}\n\n"
                f"🗂️ *Topics*: {topics_list}\n"
                f"📊 *Difficulty*: {easy_count}E · {medium_count}M · {hard_count}H\n\n"
                f"Please review the preview cover image and approve/reject."
            )

            # Build inline keyboard markup
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data="approve"),
                    InlineKeyboardButton("❌ Reject", callback_data="reject")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send photo with buttons
            logger.info("Sending preview cover slide to Telegram chat ID: %s", self.chat_id)
            if not os.path.exists(photo_path):
                raise FileNotFoundError(f"Cover slide photo not found at: {photo_path}")
                
            with open(photo_path, "rb") as photo_file:
                message = await bot.send_photo(
                    chat_id=self.chat_id,
                    photo=photo_file,
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
                
            message_id = message.message_id

            # Create the callback handler application
            application = Application.builder().token(self.token).build()
            application.add_handler(CallbackQueryHandler(self.button_callback))

            # Initialize and start polling
            await application.initialize()
            await application.start()
            await application.updater.start_polling()

            # Launch the timeout monitor task
            timeout_task = asyncio.create_task(self.timeout_handler(application, message_id))

            # Wait loop: poll for query callback changes
            while self.result is None:
                await asyncio.sleep(0.5)

            # Cleanup and stop application
            if not timeout_task.done():
                timeout_task.cancel()

            await application.updater.stop()
            await application.stop()
            await application.shutdown()

            return self.result

        except Exception as e:
            logger.error("Exception in Telegram approval gateway: %s", str(e))
            raise

    def send_for_approval(self, photo_path: str, slide_data: dict) -> bool:
        """Synchronous wrapper to run the async approval gateway."""
        try:
            return asyncio.run(self.send_for_approval_async(photo_path, slide_data))
        except Exception as e:
            logger.error("Telegram bot runner encountered an error: %s", str(e))
            raise

if __name__ == "__main__":
    # Standalone Test
    logger.info("Running Telegram approval bot test. Sending test message...")
    
    # Check if we have generated slide_01.png or mock one
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_photo = os.path.join(base_dir, "output", "slides", "slide_01.png")
    
    # Create a mock image if the file doesn't exist
    if not os.path.exists(test_photo):
        os.makedirs(os.path.dirname(test_photo), exist_ok=True)
        # Create a tiny mock png file to satisfy file reading
        import base64
        tiny_png = b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        with open(test_photo, "wb") as f:
            f.write(base64.b64decode(tiny_png))
        logger.info("Created a tiny mock PNG for testing at: %s", test_photo)

    test_data = {
        "date": "08 Jun 2026",
        "topics": ["Polity", "Environment", "Economy"],
        "mcqs": [
            {"difficulty": "Easy"}, {"difficulty": "Medium"}, {"difficulty": "Hard"},
            {"difficulty": "Medium"}, {"difficulty": "Easy"}
        ]
    }

    try:
        bot = TelegramApprovalBot()
        print("\n[WAITING] Please check your Telegram chat and click Approve or Reject...\n")
        approved = bot.send_for_approval(test_photo, test_data)
        
        print("\n--- TELEGRAM BOT SUCCESS ---")
        print(f"Approval Result: {approved}")
        if approved:
            print("Action: Ready to Post!")
        else:
            print("Action: Run Cancelled/Rejected.")
            
    except Exception as err:
        print(f"\n--- TELEGRAM BOT FAILURE ---")
        print(f"Error: {str(err)}")
        sys.exit(1)
