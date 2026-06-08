import os
import sys
import json
import time
import argparse
import requests

# Try to import logger and config
try:
    from upsc_agent.utils.logger import logger
    from upsc_agent.utils.config import config
except ImportError:
    # Fallback to local import if run directly
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.logger import logger
    from utils.config import config

class InstagramPoster:
    def __init__(self):
        self.access_token = config.INSTAGRAM_ACCESS_TOKEN
        self.account_id = config.INSTAGRAM_ACCOUNT_ID
        self.api_version = "v19.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def upload_to_temp_host(self, file_path: str) -> str:
        """
        Uploads a local image file to tmpfiles.org to get a publicly accessible URL.
        """
        logger.info("Uploading local image to temporary host: %s", file_path)
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
                
            with open(file_path, "rb") as f:
                response = requests.post(
                    "https://tmpfiles.org/api/v1/upload", 
                    files={"file": f}, 
                    timeout=20
                )
                
            if response.status_code != 200:
                raise Exception(f"Temp host upload returned status code {response.status_code}: {response.text}")
                
            res_json = response.json()
            view_url = res_json["data"]["url"]
            # Convert viewing link to direct download link:
            # e.g., https://tmpfiles.org/12345/slide.png -> https://tmpfiles.org/dl/12345/slide.png
            direct_url = view_url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
            logger.info("Temp hosting successful. Direct URL: %s", direct_url)
            return direct_url
            
        except Exception as e:
            logger.error("Failed to upload slide image to temporary host: %s", str(e))
            raise

    def create_item_container(self, image_url: str) -> str:
        """
        Creates a media container for a single image in the carousel.
        Returns the container item creation ID.
        """
        url = f"{self.base_url}/{self.account_id}/media"
        params = {
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": self.access_token
        }
        logger.info("Creating Meta Graph media item container...")
        try:
            response = requests.post(url, params=params, timeout=15)
            res_json = response.json()
            
            if response.status_code != 200 or "id" not in res_json:
                raise Exception(f"Failed to create media container: {res_json}")
                
            container_id = res_json["id"]
            logger.info("Successfully created item container ID: %s", container_id)
            return container_id
            
        except Exception as e:
            logger.error("Error creating Meta Graph media container: %s", str(e))
            raise

    def create_carousel_container(self, item_ids: list, caption: str) -> str:
        """
        Creates the main carousel container linking the children item IDs together.
        Returns the carousel container ID.
        """
        url = f"{self.base_url}/{self.account_id}/media"
        params = {
            "media_type": "CAROUSEL",
            "children": json.dumps(item_ids),
            "caption": caption,
            "access_token": self.access_token
        }
        logger.info("Creating main carousel container combining children: %s", item_ids)
        try:
            response = requests.post(url, params=params, timeout=15)
            res_json = response.json()
            
            if response.status_code != 200 or "id" not in res_json:
                raise Exception(f"Failed to create carousel container: {res_json}")
                
            carousel_id = res_json["id"]
            logger.info("Successfully created carousel container ID: %s", carousel_id)
            return carousel_id
            
        except Exception as e:
            logger.error("Error creating Meta Graph carousel container: %s", str(e))
            raise

    def publish_carousel(self, carousel_id: str) -> str:
        """
        Publishes the finalized carousel container.
        Returns the published Instagram Post ID.
        """
        url = f"{self.base_url}/{self.account_id}/media_publish"
        params = {
            "creation_id": carousel_id,
            "access_token": self.access_token
        }
        logger.info("Publishing carousel container ID: %s", carousel_id)
        try:
            response = requests.post(url, params=params, timeout=15)
            res_json = response.json()
            
            if response.status_code != 200 or "id" not in res_json:
                raise Exception(f"Failed to publish carousel: {res_json}")
                
            post_id = res_json["id"]
            logger.info("Success! Instagram post published with ID: %s", post_id)
            return post_id
            
        except Exception as e:
            logger.error("Error publishing Meta Graph media carousel: %s", str(e))
            raise

    def generate_post_caption(self, slide_data: dict) -> str:
        """Generates post caption containing correct answers and short explanations."""
        date = slide_data.get("date", "Today")
        day = slide_data.get("day", "")
        hook = slide_data.get("hook", "Daily UPSC Practice")
        ig_handle = config.UPSC_IG_HANDLE

        answers_list = []
        for idx, mcq in enumerate(slide_data.get("mcqs", [])):
            q_num = mcq.get("q_num", idx + 1)
            topic = mcq.get("topic", "General")
            correct = mcq.get("correct", "A")
            explanation = mcq.get("explanation", "")
            answers_list.append(f"Q{q_num} ({topic}) → {correct} | {explanation}")

        answers_text = "\n".join(answers_list)

        caption = f"""🎯 {hook} — {date} {f'({day})' if day else ''}

Today's 10 MCQs cover:
🏛️ Polity  📈 Economy  🌿 Environment
🌍 IR  🔬 Science & Tech

ANSWERS & EXPLANATIONS 👇
{answers_text}

📰 Source: The Hindu + Indian Express
🔔 Follow {ig_handle} for daily MCQs at 9 AM
💬 Drop your score: 0–3 🔴 · 4–6 🟡 · 7–10 🟢

#UPSC #UPSCPrelims #CurrentAffairs #IAS #IASPreparation
#UPSCMCQs #TheHindu #IndianExpress #UPSCAspire #DailyMCQ
#Polity #Economy #Environment #GeneralStudies #GS1 #GS2 #GS3"""
        return caption

    def post(self, slide_paths: list, slide_data: dict, dry_run: bool = False) -> str:
        """
        Orchestrates uploading slides, generating caption, and publishing the carousel.
        If dry_run is True, prints caption and details without hitting endpoints.
        """
        caption = self.generate_post_caption(slide_data)

        if dry_run:
            logger.info("=== DRY RUN MODE: Instagram Poster ===")
            logger.info("Post Slide Paths:\n%s", "\n".join([f" - {p}" for p in slide_paths]))
            logger.info("Generated Instagram Caption:\n%s", caption)
            logger.info("======================================")
            return "dry_run_post_id"

        logger.info("Starting live Instagram posting sequence...")
        if len(slide_paths) != 7:
            raise ValueError(f"Expected exactly 7 slide paths, got {len(slide_paths)}")

        uploaded_urls = []
        item_ids = []

        try:
            # 1. Upload images to temporary host
            for path in slide_paths:
                direct_url = self.upload_to_temp_host(path)
                uploaded_urls.append(direct_url)

            # 2. Create media items for each carousel card
            for img_url in uploaded_urls:
                item_id = self.create_item_container(img_url)
                item_ids.append(item_id)
                # Wait briefly between items to be nice to Facebook API
                time.sleep(2)

            # 3. Create main carousel object
            carousel_id = self.create_carousel_container(item_ids, caption)
            
            # Wait for Meta servers to process container before publishing
            logger.info("Waiting 10 seconds for Meta server processing...")
            time.sleep(10)

            # 4. Publish carousel post
            post_id = self.publish_carousel(carousel_id)
            return post_id

        except Exception as e:
            logger.error("Failed to post carousel to Instagram: %s", str(e))
            raise

if __name__ == "__main__":
    # Setup CLI parser
    parser = argparse.ArgumentParser(description="Test Standalone Instagram Poster Agent")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode to preview captions")
    args = parser.parse_args()

    logger.info("Running Instagram poster agent test...")
    
    # Mock data for standalone verification
    mock_data = {
        "date": "08 Jun 2026",
        "day": "Monday",
        "hook": "Start Your Week Strong",
        "mcqs": [
            {
                "q_num": i+1,
                "topic": "Polity" if i % 2 == 0 else "Environment",
                "correct": "B",
                "explanation": f"This is mock explanation for question {i+1}."
            } for i in range(10)
        ]
    }
    
    # Resolve slides directories and paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mock_slide_paths = [os.path.join(base_dir, "output", "slides", f"slide_0{i}.png") for i in range(1, 8)]

    # Make sure mock images are created if they do not exist
    for path in mock_slide_paths:
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(b"mock_binary_data")

    try:
        poster = InstagramPoster()
        # Enforce dry-run if not passed since actual posting requires real credentials
        run_mode = args.dry_run
        if not run_mode:
            logger.warning("No --dry-run flag supplied. Since real credentials are required, executing dry-run for safety.")
            run_mode = True

        post_id = poster.post(mock_slide_paths, mock_data, dry_run=run_mode)
        print("\n--- INSTAGRAM POSTER SUCCESS ---")
        print(f"Post ID: {post_id}")
        
    except Exception as err:
        print(f"\n--- INSTAGRAM POSTER FAILURE ---")
        print(f"Error: {str(err)}")
        sys.exit(1)
