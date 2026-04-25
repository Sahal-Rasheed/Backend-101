import logging


class StructuredFormatter(logging.Formatter):
    def format(self, record):
        base = super().format(record)

        # logRecord attributes to ignore
        standard_attrs = {
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
        }

        # extract extra fields
        extra_fields = {
            k: v for k, v in record.__dict__.items() if k not in standard_attrs
        }

        if extra_fields:
            return f"{base} | {extra_fields}"

        return base


class ColorStructuredFormatter(StructuredFormatter):
    COLORS = {
        "DEBUG": "\033[37m",
        "INFO": "\033[36m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[41m",
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
