"""Central loguru configuration shared by the whole app.

Configures loguru's own sink, then bridges stdlib `logging` (used by
third-party libraries) into loguru via the standard interception recipe, so
every log line in the process goes through the same sink and format.

Deliberately does not touch Django's own `LOGGING`/`LOGGING_CONFIG` --
the "django" and "django.server" loggers attach their own handlers with
`propagate=False`, so e.g. the runserver request log line is unaffected.
"""

import logging
import sys

from loguru import logger

_configured = False


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def configure_logging(debug: bool) -> None:
    """Configure loguru as the single sink for app code and stdlib logging.

    Safe to call more than once -- only the first call takes effect.
    """
    global _configured
    if _configured:
        return
    _configured = True

    level = "DEBUG" if debug else "INFO"

    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=logging.WARNING, force=True)
