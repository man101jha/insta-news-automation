import logging
import sys
from colorama import init, Fore, Style

# Initialize colorama for cross-platform support (handles Windows ANSI terminal translation)
init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that colors the output level name based on the severity of the log record.
    """
    
    # Map severity levels to Colorama foreground colors
    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT
    }

    def format(self, record):
        """
        Formats a log record and adds color styling to the level and messages.
        """
        level_color = self.COLORS.get(record.levelno, "")
        
        # Color the levelname and message parts differently for maximum readability
        levelname_styled = f"{level_color}[{record.levelname}]{Style.RESET_ALL}"
        message_styled = f"{record.msg}"
        
        # Override the levelname and msg for the formatted record copy
        record.levelname = levelname_styled
        record.msg = message_styled
        
        return super().format(record)

def get_logger(name: str = "finance_agent") -> logging.Logger:
    """
    Returns a configured Logger instance with a colored console stream handler.
    
    Args:
        name: Name of the logger, typically __name__ of the module.
    """
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers if the logger is retrieved multiple times
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Create a console handler sending logs to stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        
        # Define log message layout: [TIMESTAMP] [LEVEL] - LoggerName: Message
        log_format = "%(asctime)s %(levelname)s - %(name)s: %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
        
        # Attach the colored formatter to the console handler
        formatter = ColoredFormatter(fmt=log_format, datefmt=date_format)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        
    return logger

if __name__ == "__main__":
    # Test execution when run directly to demonstrate color coding
    logger = get_logger("logger_test")
    print("--- Console Logger Test ---")
    logger.debug("This is a DEBUG message (cyan)")
    logger.info("This is an INFO message (green)")
    logger.warning("This is a WARNING message (yellow)")
    logger.error("This is an ERROR message (red)")
    logger.critical("This is a CRITICAL message (bright red)")
