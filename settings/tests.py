import logging

from django.test import SimpleTestCase
from loguru import logger

from settings.log_config import configure_logging


class LoggingConfigTests(SimpleTestCase):
    def test_stdlib_logging_is_routed_through_loguru(self):
        configure_logging(debug=True)
        records = []
        sink_id = logger.add(records.append, format="{message}")
        try:
            logging.getLogger("some.third.party.lib").warning("hello from stdlib")
        finally:
            logger.remove(sink_id)

        messages = [r.record["message"] for r in records]
        self.assertIn("hello from stdlib", messages)

    def test_configure_logging_is_idempotent(self):
        configure_logging(debug=True)
        configure_logging(debug=True)
        records = []
        sink_id = logger.add(records.append, format="{message}")
        try:
            logger.info("just once")
        finally:
            logger.remove(sink_id)

        self.assertEqual(len(records), 1)
