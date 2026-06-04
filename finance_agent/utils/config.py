import os
from pathlib import Path
from dotenv import load_dotenv

# Find the project root directory (parent of the utils directory)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables from the .env file in the project root
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH)

class Config:
    """
    Configuration manager for the multi-agent system.
    Loads variables from the environment and validates their presence.
    """
    
    # Groq configuration
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    # Reddit configuration
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
    
    # Canva configuration
    CANVA_ACCESS_TOKEN = os.getenv("CANVA_ACCESS_TOKEN")
    CANVA_BRAND_TEMPLATE_ID = os.getenv("CANVA_BRAND_TEMPLATE_ID")
    
    # Telegram configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    # Instagram configuration
    INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")

    @classmethod
    def validate_keys(cls) -> list[str]:
        """
        Validates that required configuration keys are set and not placeholder values.
        Returns a list of error messages for any missing or invalid keys.
        """
        errors = []
        required_configs = {
            "GROQ_API_KEY": cls.GROQ_API_KEY,
            "REDDIT_CLIENT_ID": cls.REDDIT_CLIENT_ID,
            "REDDIT_CLIENT_SECRET": cls.REDDIT_CLIENT_SECRET,
            "REDDIT_USER_AGENT": cls.REDDIT_USER_AGENT,
            "TELEGRAM_BOT_TOKEN": cls.TELEGRAM_BOT_TOKEN,
            "TELEGRAM_CHAT_ID": cls.TELEGRAM_CHAT_ID,
        }
        
        for name, value in required_configs.items():
            if not value:
                errors.append(f"Missing required environment variable: {name}")
            elif "your_" in value or "placeholder" in value or value.startswith("gsk_your"):
                errors.append(f"Environment variable '{name}' contains placeholder values.")
                
        return errors

if __name__ == "__main__":
    # Test execution when script is run directly
    print("--- Config Validation Test ---")
    print(f"Project root resolved to: {PROJECT_ROOT}")
    print(f"Loading env from: {ENV_PATH} (exists: {ENV_PATH.exists()})")
    
    validation_errors = Config.validate_keys()
    if validation_errors:
        print("Validation Status: FAILED")
        for err in validation_errors:
            print(f" - {err}")
    else:
        print("Validation Status: SUCCESS")
