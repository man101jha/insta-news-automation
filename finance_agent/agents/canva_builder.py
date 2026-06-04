import asyncio
import json
import os
import time
import requests
from pathlib import Path
from playwright.async_api import async_playwright
from utils.config import Config
from utils.logger import get_logger

# Initialize module logger
logger = get_logger("canva_builder")

# Create local output directory paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

class CanvaBuilder:
    """
    Agent responsible for rendering the carousel copy into high-quality 4:5 aspect ratio images
    using local HTML/CSS + Playwright, and then syncing them to Canva via the Connect API.
    """

    def __init__(self):
        """
        Initializes the Canva Builder Agent.
        """
        # Canva Connect API base URL
        self.base_url = "https://api.canva.com/rest/v1"
        self.access_token = Config.CANVA_ACCESS_TOKEN
        
        # Verify access token availability
        if not self.access_token or "your_" in self.access_token:
            logger.warning("CANVA_ACCESS_TOKEN is missing or contains placeholder values. Canva uploads will be skipped.")
            self.can_upload = False
        else:
            self.can_upload = True

    def _download_image(self, url: str, dest_path: Path) -> bool:
        """
        Downloads an image from a URL and saves it to dest_path.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        try:
            logger.info(f"Downloading background image from {url}...")
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                dest_path.write_bytes(r.content)
                logger.info(f"Successfully downloaded image to {dest_path.name}")
                return True
            else:
                logger.warning(f"Failed to download image (HTTP {r.status_code}) from {url}")
        except Exception as e:
            logger.error(f"Error downloading image from {url}: {str(e)}")
        return False

    def _fetch_og_image(self, url: str) -> str:
        """
        Fetches an article page and extracts its og:image or twitter:image.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        try:
            logger.info(f"Scraping og:image from article link: {url}...")
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                html = r.text
                import re
                match = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                if not match:
                    match = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', html, re.IGNORECASE)
                if not match:
                    match = re.search(r'<meta[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
                if not match:
                    match = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']twitter:image["\']', html, re.IGNORECASE)
                
                if match:
                    og_url = match.group(1).strip()
                    logger.info(f"Found og:image URL: {og_url}")
                    return og_url
                else:
                    logger.info("No og:image or twitter:image found in page HTML.")
            else:
                logger.warning(f"Failed to fetch article page (HTTP {r.status_code})")
        except Exception as e:
            logger.error(f"Error scraping og:image from {url}: {str(e)}")
        return None

    def prepare_background_images(self, slides: list[dict]):
        """
        Downloads background images for all slides. Saves them locally as bg_slide_{slide_num}.jpg.
        If an image fails to load, it falls back to a category-based stock photo.
        """
        stock_images = {
            "cover": "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?auto=format&fit=crop&w=1080&q=80",
            "cta": "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?auto=format&fit=crop&w=1080&q=80",
            "markets": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1080&q=80",
            "housing": "https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=1080&q=80",
            "banking": "https://images.unsplash.com/photo-1501167786227-4cba60f6d58f?auto=format&fit=crop&w=1080&q=80",
            "gold": "https://images.unsplash.com/photo-1610375461246-83df859d8222?auto=format&fit=crop&w=1080&q=80",
            "rupee": "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?auto=format&fit=crop&w=1080&q=80",
            "general": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1080&q=80"
        }
        
        for slide in slides:
            slide_num = slide.get("slide_num")
            slide_type = slide.get("type", "news")
            tag = slide.get("tag", "").upper()
            link = slide.get("link", "")
            
            dest_path = OUTPUT_DIR / f"bg_slide_{slide_num}.jpg"
            
            # Select fallback URL based on type/category
            fallback_url = stock_images["general"]
            if slide_type == "cover":
                fallback_url = stock_images["cover"]
            elif slide_type == "cta":
                fallback_url = stock_images["cta"]
            else:
                tag_lower = tag.lower()
                if any(x in tag_lower for x in ["market", "stock", "nifty", "sensex", "trading"]):
                    fallback_url = stock_images["markets"]
                elif any(x in tag_lower for x in ["housing", "real estate", "property", "home"]):
                    fallback_url = stock_images["housing"]
                elif any(x in tag_lower for x in ["banking", "bank", "loan", "tax", "interest", "saving", "fund", "mutual"]):
                    fallback_url = stock_images["banking"]
                elif any(x in tag_lower for x in ["gold", "commodity", "silver"]):
                    fallback_url = stock_images["gold"]
                elif any(x in tag_lower for x in ["rupee", "money", "wealth", "economy", "budget", "policy"]):
                    fallback_url = stock_images["rupee"]
            
            download_success = False
            
            # If news slide and has a link, try to scrape first
            if slide_type == "news" and link:
                og_url = self._fetch_og_image(link)
                if og_url:
                    download_success = self._download_image(og_url, dest_path)
            
            # Fallback if scraping wasn't tried or failed
            if not download_success:
                logger.info(f"Using fallback background for slide {slide_num} (Category: {tag or slide_type}).")
                self._download_image(fallback_url, dest_path)

    def generate_html_content(self, slides: list[dict]) -> str:
        """
        Creates a single, highly stylized HTML document containing all 7 slides.
        Uses CSS to style slides exactly matching the user's square dark-mode design system.
        """
        slide_divs = []
        
        for slide in slides:
            slide_num = slide.get("slide_num")
            tag = slide.get("tag", "NEWS")
            headline = slide.get("headline", "")
            body = slide.get("body", "")
            slide_type = slide.get("type", "news")
            source = slide.get("source", "")
            
            # Extract metrics for footer pills
            stat1 = slide.get("stat1", "")
            stat1_label = slide.get("stat1_label", "")
            stat2 = slide.get("stat2", "")
            stat2_label = slide.get("stat2_label", "")
            
            # Format slide number for news slides (e.g. 1 -> "01", 2 -> "02")
            formatted_num = f"{slide_num - 1:02d}"
            
            # SVG Right Arrow for bottom-right circular button
            arrow_svg = """
            <svg viewBox="0 0 24 24">
                <path d="M5 12h14M12 5l7 7-7 7" stroke="#D4AF37" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            """
            
            # Build metric pills HTML
            pills_html = ""
            if stat1 and stat1_label:
                pills_html += f"""
                <div class="metric-pill">
                    <span class="bold">{stat1}</span> {stat1_label}
                </div>
                """
            if stat2 and stat2_label:
                pills_html += f"""
                <div class="metric-pill">
                    <span class="bold">{stat2}</span> {stat2_label}
                </div>
                """
                
            pills_container_html = ""
            if pills_html:
                pills_container_html = f"""
                <div class="metric-pills-container">
                    {pills_html}
                </div>
                """
            
            # Build slide-specific content
            if slide_type == "cover":
                content_html = f"""
                <div class="line-top"></div>
                <div class="cover-container">
                    <div class="category-tag">{tag}</div>
                    <div class="cover-title">{headline}</div>
                    <div class="cover-subtitle">{body}</div>
                </div>
                <div class="arrow-circle">{arrow_svg}</div>
                <div class="line-bottom"></div>
                """
            elif slide_type == "cta":
                content_html = f"""
                <div class="line-top"></div>
                <div class="cta-container">
                    <div class="category-tag">{tag}</div>
                    <div class="cta-headline">{headline}</div>
                    <div class="cta-body">{body}</div>
                </div>
                <div class="line-bottom"></div>
                """
            else:
                # Standard news slide
                content_html = f"""
                <div class="line-top"></div>
                <div class="slide-number-circle">{formatted_num}</div>
                <div class="news-container">
                    <div class="category-tag">{tag}</div>
                    <div class="news-headline">{headline}</div>
                    <div class="news-body">{body}</div>
                    <div class="news-source">Source: {source}</div>
                    {pills_container_html}
                </div>
                <div class="arrow-circle">{arrow_svg}</div>
                <div class="line-bottom"></div>
                """
                
            # Apply local background image with dim slate-black overlay gradient
            slide_divs.append(f"""
            <div class="slide" id="slide-{slide_num}" style="background-image: linear-gradient(rgba(7, 10, 16, 0.82), rgba(7, 10, 16, 0.90)), url('bg_slide_{slide_num}.jpg');">
                {content_html}
            </div>
            """)
            
        html_slides = "\n".join(slide_divs)
        
        # Complete HTML with embedded styling and Google Fonts
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,500;0,700;1,400&display=swap" rel="stylesheet">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background-color: #070a10;
                    font-family: 'Inter', sans-serif;
                }}
                .slide {{
                    width: 1080px;
                    height: 1080px;
                    background-size: cover;
                    background-position: center;
                    background-repeat: no-repeat;
                    color: #F3F4F6;
                    position: relative;
                    box-sizing: border-box;
                    padding: 100px 80px;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    overflow: hidden;
                    margin-bottom: 20px;
                }}
                
                /* Horizontal framing rules matching design */
                .line-top {{
                    position: absolute;
                    top: 60px;
                    left: 80px;
                    right: 80px;
                    height: 1.5px;
                    background-color: rgba(255, 255, 255, 0.15);
                    z-index: 5;
                }}
                .line-bottom {{
                    position: absolute;
                    bottom: 60px;
                    left: 80px;
                    right: 80px;
                    height: 1.5px;
                    background-color: rgba(255, 255, 255, 0.15);
                    z-index: 5;
                }}
                
                /* Center numbered circle for body slides */
                .slide-number-circle {{
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-radius: 50%;
                    width: 70px;
                    height: 70px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 10px auto 0 auto;
                    font-family: 'Playfair Display', serif;
                    font-size: 24px;
                    font-weight: 500;
                    color: #D4AF37;
                    z-index: 5;
                    position: relative;
                    background-color: rgba(9, 13, 21, 0.8);
                }}
                
                /* Category Tag styling */
                .category-tag {{
                    background-color: #D4AF37;
                    color: #0B111E;
                    border-radius: 8px;
                    padding: 6px 14px;
                    font-size: 13px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    text-transform: uppercase;
                    display: inline-block;
                    margin-bottom: 20px;
                    font-family: 'Inter', sans-serif;
                }}
                
                /* Next Page circular button */
                .arrow-circle {{
                    position: absolute;
                    bottom: 80px;
                    right: 80px;
                    border: 1.5px solid #D4AF37;
                    border-radius: 50%;
                    width: 60px;
                    height: 60px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 5;
                    background-color: rgba(9, 13, 21, 0.6);
                }}
                .arrow-circle svg {{
                    width: 24px;
                    height: 24px;
                }}
                
                /* Cover page typography styling */
                .cover-container {{
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    height: 100%;
                    padding-bottom: 60px;
                    z-index: 3;
                    position: relative;
                }}
                .cover-title {{
                    font-family: 'Playfair Display', serif;
                    font-size: 58px;
                    line-height: 1.3;
                    font-weight: 700;
                    margin-bottom: 30px;
                    color: #FAF8F6;
                    letter-spacing: -0.5px;
                }}
                .cover-subtitle {{
                    font-family: 'Inter', sans-serif;
                    font-size: 14px;
                    font-weight: 600;
                    letter-spacing: 1.5px;
                    line-height: 1.5;
                    color: #D1D5DB;
                    text-transform: uppercase;
                }}
                
                /* News page typography styling */
                .news-container {{
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    height: 100%;
                    padding-bottom: 60px;
                    z-index: 3;
                    position: relative;
                }}
                .news-headline {{
                    font-family: 'Playfair Display', serif;
                    font-size: 44px;
                    line-height: 1.25;
                    font-weight: 700;
                    color: #FAF8F6;
                    margin-bottom: 15px;
                    letter-spacing: -0.5px;
                    border-left: 5px solid #D4AF37;
                    padding-left: 20px;
                    background: rgba(0, 0, 0, 0.55);
                    padding-top: 8px;
                    padding-bottom: 8px;
                    border-radius: 0 8px 8px 0;
                }}
                .news-body {{
                    font-family: 'Inter', sans-serif;
                    font-size: 21px;
                    line-height: 1.55;
                    color: #D1D5DB;
                    font-weight: 400;
                    background: rgba(0, 0, 0, 0.55);
                    padding: 12px 18px;
                    border-radius: 8px;
                    margin-bottom: 15px;
                }}
                .news-source {{
                    font-family: 'Inter', sans-serif;
                    font-size: 13px;
                    font-weight: 700;
                    color: #9CA3AF;
                    text-transform: uppercase;
                    letter-spacing: 1.5px;
                    margin-bottom: 15px;
                    margin-top: -5px;
                    z-index: 4;
                    position: relative;
                }}
                
                /* Metric pills container */
                .metric-pills-container {{
                    display: flex;
                    gap: 15px;
                    z-index: 4;
                    position: relative;
                }}
                .metric-pill {{
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 20px;
                    padding: 8px 18px;
                    font-size: 15px;
                    color: #E5E7EB;
                    font-family: 'Inter', sans-serif;
                    display: flex;
                    align-items: center;
                }}
                .metric-pill .bold {{
                    font-weight: 700;
                    color: #D4AF37;
                    margin-right: 6px;
                }}
                
                /* Call-to-action page styling */
                .cta-container {{
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    height: 100%;
                    padding-bottom: 40px;
                    z-index: 3;
                    position: relative;
                }}
                .cta-headline {{
                    font-family: 'Playfair Display', serif;
                    font-size: 58px;
                    line-height: 1.3;
                    font-weight: 700;
                    margin-bottom: 25px;
                    color: #FAF8F6;
                    letter-spacing: -0.5px;
                }}
                .cta-body {{
                    font-family: 'Inter', sans-serif;
                    font-size: 24px;
                    line-height: 1.5;
                    color: #9CA3AF;
                    font-weight: 500;
                }}
            </style>
        </head>
        <body>
            {html_slides}
        </body>
        </html>
        """
        return html_template

    async def build_slides_locally(self, slides: list[dict]) -> list[str]:
        """
        Renders the slide deck locally as high-resolution images.
        Uses Playwright's Async API to set viewport and screenshot each div element.
        """
        logger.info("Preparing background images for slides...")
        self.prepare_background_images(slides)
        
        logger.info("Initializing Playwright screenshot capture...")
        html_content = self.generate_html_content(slides)
        
        # Save temporary HTML file
        temp_html_path = OUTPUT_DIR / "temp_carousel.html"
        temp_html_path.write_text(html_content, encoding="utf-8")
        
        image_paths = []

        
        try:
            async with async_playwright() as p:
                # Launch headless browser
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Set viewport to 1080x1080 for exact aspect ratio rendering
                await page.set_viewport_size({"width": 1080, "height": 1080})
                
                # Open local file path
                await page.goto(temp_html_path.absolute().as_uri())
                
                # Wait for Google fonts and layout to completely settle
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(1000) # Quick safety buffer for font rendering
                
                for slide in slides:
                    slide_num = slide.get("slide_num")
                    element_id = f"#slide-{slide_num}"
                    
                    # Capture screenshot of specific slide container
                    slide_element = page.locator(element_id)
                    output_file_name = f"slide_{slide_num}.png"
                    output_path = OUTPUT_DIR / output_file_name
                    
                    await slide_element.screenshot(path=str(output_path))
                    image_paths.append(str(output_path))
                    logger.info(f"Generated local slide image: {output_path.name}")
                    
                await browser.close()
                
        except Exception as e:
            logger.error(f"Error during Playwright rendering: {str(e)}")
        finally:
            # Clean up temporary HTML file
            if temp_html_path.exists():
                temp_html_path.unlink()
                
        return image_paths

    def upload_to_canva(self, image_paths: list[str]) -> list[str]:
        """
        Uploads the local slide images to Canva using the Connect API.
        Canva Rate Limit: 30 requests per minute per user.
        
        Args:
            image_paths: List of absolute paths to local slide images.
        Returns:
            List of Canva asset IDs or empty if upload is skipped.
        """
        if not self.can_upload:
            logger.info("Canva upload skipped (access token is unconfigured).")
            return []
            
        logger.info("Starting Canva asset upload process...")
        uploaded_asset_ids = []
        
        for path_str in image_paths:
            path = Path(path_str)
            if not path.exists():
                logger.warning(f"File not found for Canva upload: {path}")
                continue
                
            logger.info(f"Uploading {path.name} to Canva Connect API...")
            
            # Prepare metadata header (required by Canva API)
            metadata = {"name": path.name}
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Asset-Upload-Metadata": json.dumps(metadata),
                "Content-Type": "application/octet-stream"
            }
            
            try:
                # Read file as binary stream
                with open(path, "rb") as image_file:
                    binary_data = image_file.read()
                    
                # Create asset upload job (asynchronous endpoint)
                response = requests.post(
                    f"{self.base_url}/asset-uploads",
                    headers=headers,
                    data=binary_data,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    job_info = response.json()
                    job_id = job_info.get("job", {}).get("id")
                    logger.info(f"Upload job started for {path.name}. Job ID: {job_id}")
                    
                    # Poll the job status until it succeeds or fails
                    asset_id = self._poll_upload_job(job_id)
                    if asset_id:
                        uploaded_asset_ids.append(asset_id)
                else:
                    logger.error(f"Canva API error {response.status_code}: {response.text}")
                    
            except Exception as e:
                logger.error(f"Failed to upload {path.name} to Canva: {str(e)}")
                
        return uploaded_asset_ids

    def _poll_upload_job(self, job_id: str) -> str:
        """
        Polls the Canva asset upload status until complete.
        
        Args:
            job_id: The ID of the Canva upload job.
        Returns:
            The created Canva Asset ID if successful, otherwise None.
        """
        headers = {"Authorization": f"Bearer {self.access_token}"}
        max_attempts = 15
        
        for attempt in range(max_attempts):
            time.sleep(2.0)  # Wait 2 seconds between checks
            try:
                response = requests.get(
                    f"{self.base_url}/asset-uploads/{job_id}",
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    status_info = response.json().get("job", {})
                    status = status_info.get("status")
                    
                    if status == "success":
                        asset_id = status_info.get("asset", {}).get("id")
                        logger.info(f"Canva asset upload completed successfully. Asset ID: {asset_id}")
                        return asset_id
                    elif status == "failed":
                        error_msg = status_info.get("error", {}).get("message")
                        logger.error(f"Canva upload job failed: {error_msg}")
                        return None
                    else:
                        logger.debug(f"Canva upload job status: {status} (Attempt {attempt+1}/{max_attempts})")
                else:
                    logger.warning(f"Error polling job status (HTTP {response.status_code}): {response.text}")
                    
            except Exception as e:
                logger.error(f"Exception during Canva job status polling: {str(e)}")
                
        logger.error("Canva asset upload job timed out.")
        return None

if __name__ == "__main__":
    # Test execution
    print("--- Canva Slide Builder Agent Test ---")
    
    # Mock data mirroring the format from Step 4
    mock_slides = [
        {
            "slide_num": 1,
            "headline": "5 Finance Headlines Every Indian Should Know This Week",
            "body": "SWIPE TO SEE SHORT, EASY UPDATES THAT MATTER TO YOUR MONEY",
            "type": "cover"
        },
        {
            "slide_num": 2,
            "headline": "$1 Billion Green Housing Push",
            "body": "IFC and HDFC Capital launch a $1 billion fund for green affordable housing in India. This will boost sustainable urban and semi-urban residential spaces.",
            "type": "news"
        },
        {
            "slide_num": 3,
            "headline": "12% Return Is Excellent",
            "body": "HSBC Mutual Fund CEO Kailash Kulkarni advises retail investors to keep return expectations realistic, stressing that a 12% annual return is a solid market beat.",
            "type": "news"
        },
        {
            "slide_num": 4,
            "headline": "Markets Recover 700 Points",
            "body": "Sensex and Nifty bounce back sharply from early morning lows, supported by dropping crude oil prices and a strengthening rupee, boosting local sentiment.",
            "type": "news"
        },
        {
            "slide_num": 5,
            "headline": "Avoid Chasing IT Stock Rallies",
            "body": "Market experts recommend focusing portfolio allocation towards power and steel sectors rather than chasing short-term IT runups to build stable wealth.",
            "type": "news"
        },
        {
            "slide_num": 6,
            "headline": "Build Rs 100 Crore Wealth",
            "body": "Edelweiss MF CEO Radhika Gupta details compounding tips to build substantial wealth, highlighting systematic asset allocation and regular monthly savings.",
            "type": "news"
        },
        {
            "slide_num": 7,
            "headline": "Stay Money Smart, Every Week",
            "body": "Follow for quick finance news & tips",
            "type": "cta"
        }
    ]
    
    builder = CanvaBuilder()
    
    # 1. Render slide deck locally
    local_images = asyncio.run(builder.build_slides_locally(mock_slides))
    print(f"\nRendered {len(local_images)} slide images:")
    for path in local_images:
        print(f" - {path} (exists: {os.path.exists(path)})")
        
    # 2. Upload to Canva if configured
    if builder.can_upload:
        asset_ids = builder.upload_to_canva(local_images)
        print(f"Uploaded to Canva. Asset IDs: {asset_ids}")
    else:
        print("\nCanva token not set. Local files generated successfully in 'finance_agent/output/'.")
