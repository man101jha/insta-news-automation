import json
import os
import time
import requests
from pathlib import Path
from utils.config import Config
from utils.logger import get_logger

# Initialize module logger
logger = get_logger("instagram_poster")

class InstagramPoster:
    """
    Agent responsible for publishing carousel slide decks to Instagram.
    Handles temporary hosting of local image assets and orchestrates the multi-step Graph API carousel posting.
    """
    
    def __init__(self):
        """
        Initializes the Instagram Poster.
        """
        self.access_token = Config.INSTAGRAM_ACCESS_TOKEN
        self.ig_user_id = Config.INSTAGRAM_BUSINESS_ACCOUNT_ID
        self.api_version = "v19.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        # Verify access credentials
        if (not self.access_token or 
            not self.ig_user_id or 
            "your_" in self.access_token or 
            "your_" in self.ig_user_id):
            logger.warning("Instagram credentials missing or contains placeholders. Auto-publishing will be skipped.")
            self.can_post = False
        else:
            self.can_post = True

    def upload_to_temp_host(self, local_path_str: str) -> str:
        """
        Uploads a local image file to a temporary public host so Meta can fetch it.
        Uses Litterbox (litterbox.catbox.moe), a free temporary file hosting service
        where uploaded files expire and are automatically deleted after 1 hour (perfect for Instagram Graph API fetching).
        
        Args:
            local_path_str: Local file path of the slide image.
        Returns:
            The public URL of the uploaded image.
        """
        path = Path(local_path_str)
        if not path.exists():
            raise FileNotFoundError(f"Slide file not found for hosting: {local_path_str}")
            
        logger.info(f"Uploading {path.name} to temporary host (Litterbox)...")
        
        # Litterbox upload endpoint
        url = "https://litterbox.catbox.moe/resources/internals/api.php"
        
        files = {
            "fileToUpload": (path.name, open(path, "rb"), "image/png")
        }
        data = {
            "reqtype": "fileupload",
            "time": "1h"  # Set file lifespan to 1 hour (plenty of time for Meta to fetch it)
        }
        
        try:
            # Send file to Litterbox
            response = requests.post(url, files=files, data=data, timeout=30.0)
            
            # Close file streams safely
            files["fileToUpload"][1].close()
            
            if response.status_code == 200:
                public_url = response.text.strip()
                logger.info(f"Successfully hosted slide. Public URL: {public_url}")
                return public_url
            else:
                raise Exception(f"Litterbox server returned HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"Error hosting slide image {path.name}: {str(e)}")
            raise

    def wait_for_container(self, container_id: str) -> bool:
        """
        Polls the Facebook Graph API to check if a media container has finished processing.
        Instagram requires containers to be fully loaded and ready before publishing.
        
        Args:
            container_id: The ID of the container to check.
        Returns:
            True if ready, False if failed or timed out.
        """
        url = f"{self.base_url}/{container_id}"
        params = {
            "fields": "status_code",
            "access_token": self.access_token
        }
        
        max_attempts = 15
        for attempt in range(max_attempts):
            time.sleep(5.0)  # Wait 5 seconds between checks
            try:
                response = requests.get(url, params=params, timeout=15.0)
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status_code")
                    logger.debug(f"Container {container_id} status: {status} (Attempt {attempt+1}/{max_attempts})")
                    
                    if status == "FINISHED":
                        return True
                    elif status == "ERROR":
                        err_msg = data.get("error_message") or data.get("error", {}).get("message", "Unknown container processing error")
                        logger.error(f"Container processing failed: {err_msg}")
                        return False
                else:
                    logger.warning(f"Error checking container status: {response.text}")
            except Exception as e:
                logger.error(f"Exception checking container status: {str(e)}")
                
        logger.error(f"Container {container_id} status check timed out.")
        return False

    def post_carousel(self, image_paths: list[str], caption: str) -> str:
        """
        Orchestrates the multi-step carousel posting flow on Instagram.
        1. Uploads slides to public hosting.
        2. Creates Instagram media items (child containers) for each slide.
        3. Creates parent Carousel container linking the items.
        4. Publishes the parent container.
        
        Args:
            image_paths: List of local absolute paths to slide PNGs.
            caption: Caption text to accompany the post.
        Returns:
            Published Instagram Post ID or None.
        """
        if not self.can_post:
            logger.info("Instagram posting skipped (credentials are not configured).")
            return None
            
        logger.info(f"Starting Instagram carousel posting flow for {len(image_paths)} slides...")
        
        public_urls = []
        try:
            # Step 1: Upload images to public hosting
            for idx, path in enumerate(image_paths):
                url = self.upload_to_temp_host(path)
                public_urls.append(url)
                # Small rate-limit protection sleep
                time.sleep(1.0)
        except Exception as e:
            logger.error(f"Aborting Instagram post: Media hosting failed. Details: {str(e)}")
            return None
            
        # Step 2: Create child containers
        child_ids = []
        logger.info("Creating Instagram child containers...")
        
        for idx, img_url in enumerate(public_urls):
            url = f"{self.base_url}/{self.ig_user_id}/media"
            payload = {
                "image_url": img_url,
                "is_carousel_item": "true",
                "access_token": self.access_token
            }
            
            try:
                response = requests.post(url, data=payload, timeout=20.0)
                if response.status_code == 200:
                    child_id = response.json().get("id")
                    child_ids.append(child_id)
                    logger.info(f"Created child container {idx+1}/{len(public_urls)}: {child_id}")
                else:
                    logger.error(f"Failed to create child container {idx+1}: {response.text}")
                    return None
            except Exception as e:
                logger.error(f"Error creating child container: {str(e)}")
                return None
                
        # Wait for all child containers to process
        logger.info("Verifying all child containers are ready...")
        for cid in child_ids:
            if not self.wait_for_container(cid):
                logger.error(f"Child container {cid} was not processed successfully. Aborting.")
                return None
                
        # Step 3: Create parent carousel container
        logger.info("Creating parent carousel container...")
        parent_url = f"{self.base_url}/{self.ig_user_id}/media"
        
        # Meta expects children to be formatted as a JSON array of strings
        payload = {
            "media_type": "CAROUSEL",
            "caption": caption,
            "children": json.dumps(child_ids),
            "access_token": self.access_token
        }
        
        try:
            response = requests.post(parent_url, data=payload, timeout=20.0)
            if response.status_code == 200:
                parent_id = response.json().get("id")
                logger.info(f"Successfully created parent carousel container: {parent_id}")
            else:
                logger.error(f"Failed to create parent carousel container: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating parent container: {str(e)}")
            return None
            
        # Wait for parent container to process
        if not self.wait_for_container(parent_id):
            logger.error(f"Parent container {parent_id} failed processing. Aborting.")
            return None
            
        # Step 4: Publish the carousel
        logger.info(f"Publishing carousel post {parent_id} to Instagram...")
        publish_url = f"{self.base_url}/{self.ig_user_id}/media_publish"
        publish_payload = {
            "creation_id": parent_id,
            "access_token": self.access_token
        }
        
        try:
            response = requests.post(publish_url, data=publish_payload, timeout=20.0)
            if response.status_code == 200:
                post_id = response.json().get("id")
                logger.info(f"[SUCCESS] Carousel posted successfully to Instagram. Post ID: {post_id}")
                return post_id
            else:
                logger.error(f"Failed to publish carousel: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error publishing carousel: {str(e)}")
            return None

if __name__ == "__main__":
    # Test execution
    print("--- Instagram Poster Agent Test ---")
    poster = InstagramPoster()
    
    # Check mock execution
    if poster.can_post:
        print("Instagram configuration detected. Standalone publication requires actual images. Use test_flow.py to run end-to-end.")
    else:
        print("Instagram poster initialized in mock mode (no credentials in .env).")
