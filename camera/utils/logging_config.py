import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime

def setup_logging(log_level=logging.INFO, log_dir="/var/log/helmet_camera"):
    """
    Setup comprehensive logging for the helmet camera system
    
    Args:
        log_level: Logging level (default: INFO)
        log_dir: Directory for log files
    """
    
    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d')
    log_file = log_path / f"helmet_camera_{timestamp}.log"
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler for immediate feedback
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for persistent logging
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # System journal handler (systemd journal)
    try:
        from systemd.journal import JournalHandler
        journal_handler = JournalHandler(SYSLOG_IDENTIFIER='helmet_camera')
        journal_handler.setLevel(logging.INFO)
        journal_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        root_logger.addHandler(journal_handler)
        logging.info("Journal logging enabled")
    except ImportError:
        logging.warning("systemd.journal not available, journal logging disabled")
    
    # Syslog handler as fallback
    try:
        syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
        syslog_handler.setLevel(logging.WARNING)
        syslog_handler.setFormatter(logging.Formatter('helmet_camera: %(levelname)s - %(message)s'))
        root_logger.addHandler(syslog_handler)
        logging.info("Syslog logging enabled")
    except Exception as e:
        logging.warning(f"Syslog logging not available: {e}")
    
    logging.info(f"Logging system initialized. Log file: {log_file}")
    logging.info(f"Log level set to: {logging.getLevelName(log_level)}")
    
    return root_logger 