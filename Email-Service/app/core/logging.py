import logging


class StructuredFormatter(logging.Formatter):
    # these are all built-in LogRecord attributes to exclude
    _SKIP = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
        "taskName",
    }

    COLORS = {
        "DEBUG": "\033[37m",
        "INFO": "\033[36m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[41m",
    }
    RESET = "\033[0m"

    def format(self, record):
        record.message = record.getMessage()
        record.asctime = self.formatTime(record)

        extra = {k: v for k, v in record.__dict__.items() if k not in self._SKIP}

        base = f"[{record.asctime}] [{record.levelname}] {record.message}"
        if extra:
            base += " | " + " ".join(f"{k}={v!r}" for k, v in extra.items())

        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)

        color = self.COLORS.get(record.levelname, "")
        return f"{color}{base}{self.RESET}"


def get_structured_handler() -> logging.StreamHandler:
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    return handler


def setup_app_logger(name: str) -> logging.Logger:
    """
    Use this to get a logger in your app code.
    Only your loggers get the structured formatter.
    Celery's own loggers are untouched.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(get_structured_handler())
        logger.setLevel(logging.INFO)
        logger.propagate = False  # don't bubble up to celery root logger
    return logger
