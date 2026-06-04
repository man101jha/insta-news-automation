import asyncio
import sys
import os
from pathlib import Path
from agents.news_scraper import NewsScraper
from agents.filter_agent import FilterAgent
from agents.carousel_writer import CarouselWriter
from agents.canva_builder import CanvaBuilder
from agents.telegram_bot import TelegramApprovalBot
from agents.instagram_poster import InstagramPoster
from utils.logger import get_logger

# Setup main orchestrator logger
logger = get_logger("main_orchestrator")

def cleanup_local_files(image_paths: list[str]):
    """
    Cleans up temporary slide PNGs and background JPGs from the local output directory.
    """
    logger.info("Cleaning up temporary local slide and background files...")
    
    # 1. Clean up slide PNGs
    if image_paths:
        for img_path in image_paths:
            p = Path(img_path)
            if p.exists():
                try:
                    p.unlink()
                    logger.info(f"Deleted temporary slide: {p.name}")
                except Exception as e:
                    logger.error(f"Failed to delete temporary slide {p.name}: {str(e)}")
                    
    # 2. Clean up background JPGs (bg_slide_*.jpg)
    output_dir = Path(__file__).resolve().parent / "output"
    if output_dir.exists():
        for bg_file in output_dir.glob("bg_slide_*.jpg"):
            try:
                bg_file.unlink()
                logger.info(f"Deleted temporary background: {bg_file.name}")
            except Exception as e:
                logger.error(f"Failed to delete background file {bg_file.name}: {str(e)}")

async def main():
    logger.info("==============================================")
    logger.info("[START] STARTING INDIAN FINANCE NEWS AUTO-POST FLOW")
    logger.info("==============================================")
    
    image_paths = []
    try:
        # 1. Scrape news articles
        logger.info("--- Step 1: Scraping Finance News ---")
        scraper = NewsScraper()
        raw_articles = scraper.scrape_all()
        
        if not raw_articles:
            logger.error("No news articles scraped. Aborting flow.")
            sys.exit(1)
            
        # 2. Filter top 5 stories
        logger.info("--- Step 2: Filtering Top 5 Stories ---")
        filter_agent = FilterAgent()
        top_stories = filter_agent.filter_stories(raw_articles)
        
        if not top_stories:
            logger.error("Could not filter stories. Aborting flow.")
            sys.exit(1)
            
        # 3. Generate carousel copywriting
        logger.info("--- Step 3: Generating Carousel Slide Copy ---")
        writer = CarouselWriter()
        slides_copy = writer.write_carousel_copy(top_stories)
        
        if not slides_copy:
            logger.error("Could not write slide copywriting. Aborting flow.")
            sys.exit(1)
            
        # Attach original article links and sources to the news slides for background image fetching
        news_slide_idx = 0
        for slide in slides_copy:
            if slide.get("type") == "news" and news_slide_idx < len(top_stories):
                slide["link"] = top_stories[news_slide_idx].get("link", "")
                slide["source"] = top_stories[news_slide_idx].get("source", "")
                news_slide_idx += 1
    
        # 4. Render slide images locally
        logger.info("--- Step 4: Rendering Slides to Images ---")
        builder = CanvaBuilder()
        image_paths = await builder.build_slides_locally(slides_copy)
        
        if not image_paths or len(image_paths) != 7:
            logger.error(f"Failed to render all 7 slides (rendered: {len(image_paths)}). Aborting.")
            sys.exit(1)
            
        # 5. Upload images to Canva (Optional)
        if builder.can_upload:
            logger.info("--- Step 4b: Syncing Slide Assets to Canva ---")
            canva_ids = builder.upload_to_canva(image_paths)
            logger.info(f"Successfully uploaded {len(canva_ids)} assets to Canva.")
            
        # 6. Send Telegram approval request
        logger.info("--- Step 5: Sending Telegram Approval Preview ---")
        telegram_bot = TelegramApprovalBot()
        # Wait up to 15 minutes for approval
        is_approved = await telegram_bot.send_preview_and_wait(image_paths, timeout_minutes=15)
        
        if not is_approved:
            logger.warning("Carousel was rejected or timed out. Ending pipeline.")
            sys.exit(0)
            
        # 7. Post approved carousel to Instagram
        logger.info("--- Step 6: Publishing Carousel to Instagram Professional ---")
        poster = InstagramPoster()
        
        if poster.can_post:
            # Create a clean caption summarizing the top headlines
            caption_lines = [
                "📈 5 Indian Finance Stories You Need to Know Today!\n",
                "Swipe left to read simple, bite-sized summaries. ➡️\n"
            ]
            for idx, story in enumerate(top_stories):
                caption_lines.append(f"{idx+1}. {story.get('title')} ({story.get('link')})")
                
            caption_lines.extend([
                "\nFollow for daily simple finance news and smart money tips! 🔔",
                "\n#finance #india #stockmarket #investing #mutualfunds #personalfinance #moneytips #indianstockmarket #nifty #sensex #money #wealthcreation #financialfreedom #sharemarket"
            ])
            instagram_caption = "\n".join(caption_lines)
            
            post_id = poster.post_carousel(image_paths, instagram_caption)
            
            if post_id:
                logger.info(f"[SUCCESS] Auto-posting flow complete! Published Post ID: {post_id}")
            else:
                logger.error("[FAIL] Failed to publish post on Instagram.")
                sys.exit(1)
        else:
            logger.warning("Instagram credentials not configured. Skipping Instagram publishing step.")
            logger.info("[SUCCESS] Pipeline test run complete (Local render & Telegram approval successful).")
            
    finally:
        # Perform automatic cleanup of all generated slide PNGs and background JPGs
        cleanup_local_files(image_paths)


if __name__ == "__main__":
    # Run the main async routine
    asyncio.run(main())
