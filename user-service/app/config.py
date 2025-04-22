import os
import json
import logging.config
from datetime import datetime

# JWT secret key
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default_jwt_secret_key')

# Flask secret key
SECRET_KEY = os.getenv('SECRET_KEY', 'default_flask_secret_key')

# Logging Configuration
class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "service": "user-service"
        }
        
        if hasattr(record, 'user_id'):
            log_record["user_id"] = record.user_id
            
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def setup_logging():
    """Set up logging configuration for structured logs"""
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': JsonFormatter,
            },
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'json',
                'level': 'DEBUG',
                'stream': 'ext://sys.stdout',
            },
            'file': {
                'class': 'logging.FileHandler',
                'formatter': 'json',
                'level': 'INFO',
                'filename': os.getenv('LOG_FILE', 'app.log'),
                'mode': 'a',
            }
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['console', 'file'],
                'level': os.getenv('LOG_LEVEL', 'INFO'),
                'propagate': True
            }
        }
    }
    
    logging.config.dictConfig(logging_config)
    return logging.getLogger('user-service')
