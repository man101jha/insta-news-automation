import logging
import colorlog

def setup_logger(name="upsc_agent"):
    """
    Sets up a colored console logger.
    Format: [HH:MM:SS] LEVEL — message
    Colors: INFO=green, WARNING=yellow, ERROR=red, DEBUG=cyan
    """
    # Create the logger object
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Return logger immediately if handler already exists to avoid duplicate logs
    if logger.handlers:
        return logger

    # Define the log formats and color themes
    # The format is set to: [HH:MM:SS] LEVEL — message
    formatter = colorlog.ColoredFormatter(
        fmt="[%(asctime)s] %(log_color)s%(levelname)-7s%(reset)s — %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={},
        style='%'
    )

    # Set up console logging stream handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# Export a single global logger instance
logger = setup_logger()
