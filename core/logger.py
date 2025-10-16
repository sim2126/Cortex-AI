import logging
import sys
from pythonjsonlogger import jsonlogger

def get_logger(name: str):
    """
    Configures and returns a logger that outputs structured JSON.
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
