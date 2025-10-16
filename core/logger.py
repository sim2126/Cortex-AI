import logging
import sys
from pythonjsonlogger import jsonlogger

def get_logger(name: str):
    """
    Configures and returns a logger that outputs structured JSON.
    """
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers if the logger is already configured
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    
    # Use a custom format for the JSON logs
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
