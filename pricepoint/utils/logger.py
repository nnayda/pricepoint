import logging
import sys

def setup_logger(name, level=logging.INFO):
    """
    Centralized logging config used across all scripts in the repo.
    """
    formatter = logging.Formatter(
        fmt='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler for Airflow/Console
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Get the logger for the specific module
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding multiple handlers if the function is called twice
    if not logger.handlers:
        logger.addHandler(handler)
        
    # Prevent logs from double-bubbling up to the root logger
    logger.propagate = False
    
    return logger