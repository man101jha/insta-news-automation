import os
import sys
from dataclasses import dataclass
from dotenv import load_dotenv

# Try importing the logger; handle relative imports if run as a standalone script
try:
    from upsc_agent.utils.logger import logger
except ImportError:
    # Resolve paths if run directly
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.logger import logger

# Find the absolute path to the .env file in the upsc_agent folder
current_dir = os.path.dirname(os.path.abspath(__file__))
# Let's search up the tree for .env
env_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), '.env')
if not os.path.exists(env_path):
    env_path = os.path.join(os.path.dirname(current_dir), '.env')

# Load the environment variables from the identified path
load_dotenv(dotenv_path=env_path)

@dataclass(frozen=True)
class Config:
    GROQ_API_KEY: str
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str
    INSTAGRAM_ACCESS_TOKEN: str
    INSTAGRAM_ACCOUNT_ID: str
    UPSC_IG_HANDLE: str

def load_config() -> Config:
    """
    Loads environment variables and validates their presence.
    Raises ValueError if any required key is missing or empty.
    """
    try:
        # Retrieve values from environment
        groq_key = os.getenv("GROQ_API_KEY")
        tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
        tg_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        ig_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        ig_account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
        ig_handle = os.getenv("UPSC_IG_HANDLE")

        required_keys = {
            "GROQ_API_KEY": groq_key,
            "TELEGRAM_BOT_TOKEN": tg_token,
            "TELEGRAM_CHAT_ID": tg_chat_id,
            "INSTAGRAM_ACCESS_TOKEN": ig_token,
            "INSTAGRAM_ACCOUNT_ID": ig_account_id,
            "UPSC_IG_HANDLE": ig_handle,
        }

        # Check for missing or empty keys
        missing_keys = [key for key, value in required_keys.items() if not value]

        if missing_keys:
            error_msg = f"Configuration validation failed: Missing required keys: {', '.join(missing_keys)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Configuration successfully loaded
        return Config(
            GROQ_API_KEY=groq_key,
            TELEGRAM_BOT_TOKEN=tg_token,
            TELEGRAM_CHAT_ID=tg_chat_id,
            INSTAGRAM_ACCESS_TOKEN=ig_token,
            INSTAGRAM_ACCOUNT_ID=ig_account_id,
            UPSC_IG_HANDLE=ig_handle
        )

    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        raise

# Instantiate configuration on module load
try:
    config = load_config()
except Exception as e:
    # Allow python execution to exit gracefully on module loading error if not imported
    logger.error("Configuration initialization failed on startup.")
    raise
    
if __name__ == "__main__":
    print("All config loaded [OK]")
