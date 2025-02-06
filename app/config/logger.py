import contextvars
import logging
import time

correlation_id_ctx = contextvars.ContextVar("correlation_id", default=None)

class LoggingFormatter(logging.Formatter):
    fmt = '[%(asctime)s] [%(correlation_id)s] - %(levelname)s :: %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'

    def __init__(self):
        super().__init__(self.fmt, self.datefmt)

    def formatTime(self, record, datefmt=None):
        ct = time.localtime(record.created)
        formatted_time = time.strftime(self.datefmt, ct)
        return f'\033[38;5;214m{formatted_time}\033[0m'

    def format(self, record):
        correlation_id = correlation_id_ctx.get("N/A")
        record.correlation_id = f'\033[36m{correlation_id}\033[0m'
        
        levelname_colors = {
            'DEBUG': '\033[34m',
            'INFO': '\033[32m',
            'WARNING': '\033[33m',
            'ERROR': '\033[31m',
            'CRITICAL': '\033[35m',
        }

        reset = '\033[0m'
        padded_levelname = f'{levelname_colors.get(record.levelname, "\033[0m")}{record.levelname:8}{reset}'
        record.levelname = padded_levelname
        
        return super().format(record)


LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            '()': LoggingFormatter,
        },
        'access': {
            '()': LoggingFormatter,
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
        'access': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'access',
        },
    },
    'loggers': {
        'uvicorn': {
            'level': 'INFO',
            'handlers': ['default'],
            'formatter': 'default',
            'propagate': False,
        },
        'uvicorn.error': {
            'level': 'INFO',
            'handlers': ['default'],
            'formatter': 'default',
            'propagate': False,
        },
        'uvicorn.access': {
            'level': 'INFO',
            'handlers': ['access'],
            'formatter': 'access',
            'propagate': False,
        },
        'httpx': {
            'level': 'INFO',
            'handlers': ['default'],
            'propagate': False,
        },
    },
}

logger = logging.getLogger("uvicorn")