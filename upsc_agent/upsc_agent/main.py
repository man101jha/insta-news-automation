import os
import sys
import datetime
import argparse

# Try to import logger, config, and agent classes
try:
    from upsc_agent.utils.logger import logger
    from upsc_agent.utils.config import config
    from upsc_agent.agents.news_scraper import NewsScraper
    from upsc_agent.agents.mcq_generator import MCQGenerator
    from upsc_agent.agents.slide_builder import SlideBuilder
    from upsc_agent.agents.telegram_bot import TelegramApprovalBot
    from upsc_agent.agents.instagram_poster import InstagramPoster
except ImportError:
    # Resolve paths if run directly
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from utils.logger import logger
    from utils.config import config
    from agents.news_scraper import NewsScraper
    from agents.mcq_generator import MCQGenerator
    from agents.slide_builder import SlideBuilder
    from agents.telegram_bot import TelegramApprovalBot
    from agents.instagram_poster import InstagramPoster

def build_slide_data(mcq_payload: dict) -> dict:
    """
    Assembles the structured data contract required by the slide builder.
    Rotates headline hooks and motivational quotes according to the day of the week.
    """
    today = datetime.date.today()
    day_name = today.strftime("%A")
    date_str = today.strftime("%d %b %Y")
    weekday = today.weekday()  # Monday is 0, Sunday is 6

    # Rotating Hooks (Mon-Sun)
    hooks = {
        0: "Start Your Week Strong",
        1: "Tuesday Test Yourself",
        2: "Midweek UPSC Drill",
        3: "Thursday Current Affairs",
        4: "Friday Final Push",
        5: "Weekend Revision MCQs",
        6: "Sunday UPSC Practice"
    }

    # Rotating Quotes (Mon-Sun)
    quotes = {
        0: "The UPSC exam is not about studying more. It's about studying smarter — every single day.",
        1: "Consistency beats intensity. Show up for 10 questions every morning.",
        2: "One newspaper. One hour. Ten questions. That's how toppers are made.",
        3: "Your rank tomorrow depends on what you practice today.",
        4: "Small daily inputs lead to extraordinary annual outputs.",
        5: "Discipline is choosing between what you want now and what you want most.",
        6: "Rest. Reflect. Revise. The topper you want to be is built on Sundays."
    }

    hook = hooks.get(weekday, "Daily UPSC Revision")
    quote = quotes.get(weekday, "Consistency beats intensity.")

    # Extract distinct topics from generated MCQs
    topics_set = set()
    for m in mcq_payload.get("mcqs", []):
        topic = m.get("topic")
        if topic:
            topics_set.add(topic)
    topics = sorted(list(topics_set))

    return {
        "date": date_str,
        "day": day_name,
        "hook": hook,
        "subheadline": "Based on today's The Hindu + Indian Express",
        "topics": topics,
        "mcqs": mcq_payload.get("mcqs", []),
        "quote": quote,
        "ig_handle": config.UPSC_IG_HANDLE
    }

def cleanup():
    """
    Deletes temporary visual assets (*.html and *.png) generated in the run
    to keep workspace clean and avoid checking in huge binary files.
    """
    logger.info("Executing cleanup routine...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_dir = os.path.join(base_dir, "output", "html")
    slides_dir = os.path.join(base_dir, "output", "slides")

    # Clean HTML files
    if os.path.exists(html_dir):
        for file in os.listdir(html_dir):
            if file.endswith(".html"):
                try:
                    os.remove(os.path.join(html_dir, file))
                    logger.debug("Deleted temp HTML: %s", file)
                except Exception as e:
                    logger.error("Failed to delete html file %s: %s", file, str(e))

    # Clean PNG slides
    if os.path.exists(slides_dir):
        for file in os.listdir(slides_dir):
            if file.endswith(".png"):
                try:
                    os.remove(os.path.join(slides_dir, file))
                    logger.debug("Deleted temp PNG: %s", file)
                except Exception as e:
                    logger.error("Failed to delete png file %s: %s", file, str(e))

def run_pipeline(dry_run: bool = False, skip_approval: bool = False):
    """
    Orchestrates the entire UPSC MCQ daily publication pipeline.
    """
    logger.info("=== UPSC Daily Current Affairs Automation Pipeline Starting ===")
    
    try:
        # Step 1: Scrape today's national news
        scraper = NewsScraper()
        articles = scraper.scrape()
        logger.info("Step 1: Scraped %d raw articles successfully.", len(articles))

        # Step 2: Generate exactly 10 UPSC MCQs
        generator = MCQGenerator()
        mcq_payload = generator.generate(articles)
        logger.info("Step 2: Generated and validated 10 UPSC MCQs.")

        # Step 3: Build Slide templates and render images
        slide_data = build_slide_data(mcq_payload)
        builder = SlideBuilder()
        slide_paths = builder.render(slide_data)
        logger.info("Step 3: Compiled HTML templates and rendered %d slide screenshots.", len(slide_paths))

        # Step 4: Request approval via Telegram Bot
        if skip_approval:
            logger.info("Step 4: skip-approval flag active. Auto-approving pipeline run.")
            approved = True
        else:
            bot = TelegramApprovalBot()
            approved = bot.send_for_approval(slide_paths[0], slide_data)
            logger.info("Step 4: Approval gate completed. Decision result: %s", approved)

        # Step 5: Publish carousel to Instagram
        if approved:
            poster = InstagramPoster()
            post_id = poster.post(slide_paths, slide_data, dry_run=dry_run)
            logger.info("Step 5: Instagram publishing completed. Post ID: %s", post_id)
        else:
            logger.warning("Step 5: Pipeline skip. User rejected carousel or approval timed out.")

    except Exception as e:
        logger.error("UPSC Pipeline execution encountered a critical failure: %s", str(e))
        raise
        
    finally:
        # Step 6: Cleanup temporary HTML & PNG artifacts
        cleanup()
        logger.info("=== UPSC Daily Current Affairs Automation Pipeline Finished ===")

if __name__ == "__main__":
    # Configure command-line parser
    parser = argparse.ArgumentParser(description="UPSC MCQ automation pipeline orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Preview captions and slide paths without posting to Instagram")
    parser.add_argument("--skip-approval", action="store_true", help="Auto-approve slide preview bypassing Telegram gate")
    args = parser.parse_args()

    try:
        run_pipeline(dry_run=args.dry_run, skip_approval=args.skip_approval)
    except Exception:
        sys.exit(1)
