import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import json
from pathlib import Path

# Enhanced logging directory structure
BASE_LOGS_DIR = "logs"
LOGS_STRUCTURE = {
    "bills": "bills",
    "api": "api",
    "selenium": "selenium",
    "errors": "errors",
    "webflow": "webflow",
    "daily": "daily"
}

# Create all necessary directories
for dir_name in LOGS_STRUCTURE.values():
    Path(os.path.join(BASE_LOGS_DIR, dir_name)).mkdir(parents=True, exist_ok=True)

class EnhancedJsonFormatter(logging.Formatter):
    def format(self, record):
        json_record = {
            "timestamp": self.formatTime(record, datefmt='%Y-%m-%d %H:%M:%S.%f'),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
            "thread_id": record.thread
        }
        
        # Add custom fields if they exist
        for field in ['bill_id', 'request_id', 'endpoint', 'method', 'status_code', 'execution_time']:
            if hasattr(record, field):
                json_record[field] = getattr(record, field)
        
        # Add any extra data
        if hasattr(record, 'extra_data'):
            json_record.update(record.extra_data)
            
        # Add exception info if present
        if record.exc_info:
            json_record['exc_info'] = self.formatException(record.exc_info)
            
        return json.dumps(json_record)

def setup_logger(name="ddp_api", component=None):
    """
    Set up a logger with enhanced configuration
    :param name: Logger name
    :param component: Component name (bills, api, selenium, etc.)
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Console Handler with colored output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # Component-specific log file
    if component and component in LOGS_STRUCTURE:
        component_log_file = os.path.join(BASE_LOGS_DIR, LOGS_STRUCTURE[component], f"{component}.log")
        component_handler = RotatingFileHandler(
            component_log_file,
            maxBytes=20*1024*1024,  # 20MB
            backupCount=10
        )
        component_handler.setLevel(logging.DEBUG)
        component_handler.setFormatter(EnhancedJsonFormatter())
        logger.addHandler(component_handler)
    
    # Error log handler (for all ERROR and CRITICAL logs)
    error_handler = RotatingFileHandler(
        os.path.join(BASE_LOGS_DIR, "errors", "error.log"),
        maxBytes=10*1024*1024,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(EnhancedJsonFormatter())
    
    # Daily rotating handler for all logs
    daily_handler = TimedRotatingFileHandler(
        os.path.join(BASE_LOGS_DIR, "daily", "daily.log"),
        when="midnight",
        interval=1,
        backupCount=30
    )
    daily_handler.setLevel(logging.INFO)
    daily_handler.setFormatter(EnhancedJsonFormatter())
    
    # Add all handlers
    logger.addHandler(console_handler)
    logger.addHandler(error_handler)
    logger.addHandler(daily_handler)
    
    return logger

def get_bill_logger(bill_id, session=None, bill_number=None):
    """Create a logger specific to a bill processing request"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bill_logger_name = f"bill_{bill_id}_{timestamp}"
    logger = logging.getLogger(bill_logger_name)
    logger.setLevel(logging.DEBUG)
    
    # Create a unique log file for this bill processing
    log_filename = os.path.join(
        BASE_LOGS_DIR,
        LOGS_STRUCTURE['bills'],
        f"bill_{bill_id}_{session}_{bill_number}_{timestamp}.log"
    )
    
    # Bill-specific file handler with JSON formatting
    bill_handler = logging.FileHandler(log_filename)
    bill_handler.setLevel(logging.DEBUG)
    bill_handler.setFormatter(EnhancedJsonFormatter())
    
    # Also log to error file if needed
    error_handler = logging.FileHandler(
        os.path.join(BASE_LOGS_DIR, "errors", f"bill_{bill_id}_errors.log")
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(EnhancedJsonFormatter())
    
    logger.addHandler(bill_handler)
    logger.addHandler(error_handler)
    
    # Add bill metadata to all log records
    logger = logging.LoggerAdapter(logger, {
        'bill_id': bill_id,
        'extra_data': {
            'session': session,
            'bill_number': bill_number,
            'processing_start': timestamp,
            'log_file': log_filename
        }
    })
    
    return logger

# Create component-specific loggers
main_logger = setup_logger("ddp_api", "api")
selenium_logger = setup_logger("selenium", "selenium")
webflow_logger = setup_logger("webflow", "webflow")

# Export loggers for use in other modules
logger = main_logger  # Default logger
__all__ = ['logger', 'main_logger', 'selenium_logger', 'webflow_logger', 'setup_logger', 'get_bill_logger']