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

    def test_pymongo_debug_noise_is_suppressed(self):
        # Concrete regression guard for the originally-reported noisy library
        # (found flooding `docker compose logs`); superseded as a general
        # mechanism by test_third_party_debug_noise_is_suppressed_regardless_of_debug_flag
        # below, but kept since it pins the real-world case that triggered the fix.
        configure_logging(debug=True)
        records = []
        sink_id = logger.add(records.append, format="{message}")
        try:
            logging.getLogger("pymongo").debug("Command started")
            logging.getLogger("pymongo").warning("a real pymongo warning")
        finally:
            logger.remove(sink_id)

        messages = [r.record["message"] for r in records]
        self.assertNotIn("Command started", messages)
        self.assertIn("a real pymongo warning", messages)

    def test_refinedoc_warning_noise_is_suppressed(self):
        # refinedoc's header/footer heuristic logs a WARNING ("Candidate
        # quantity is too high for the document. Set to 1") whenever a PDF is
        # short enough that the heuristic clamps -- routine, says nothing about
        # extraction quality. configure_logging raises the refinedoc logger to
        # ERROR; genuine errors still surface. (Same fix used in the geogis
        # split_n_convert_pdf lambda.)
        configure_logging(debug=True)
        records = []
        sink_id = logger.add(records.append, format="{message}")
        try:
            logging.getLogger("refinedoc.refined_document").warning(
                "Candidate quantity is too high for the document. Set to 1"
            )
            logging.getLogger("refinedoc.refined_document").error(
                "a real refinedoc error"
            )
        finally:
            logger.remove(sink_id)

        messages = [r.record["message"] for r in records]
        self.assertNotIn(
            "Candidate quantity is too high for the document. Set to 1", messages
        )
        self.assertIn("a real refinedoc error", messages)

    def test_third_party_debug_noise_is_suppressed_regardless_of_debug_flag(self):
        configure_logging(debug=True)
        records = []
        sink_id = logger.add(records.append, format="{message}")
        try:
            logging.getLogger("some.other.chatty.lib").debug("internal debug noise")
            logging.getLogger("some.other.chatty.lib").warning("a real warning")
        finally:
            logger.remove(sink_id)

        messages = [r.record["message"] for r in records]
        self.assertNotIn("internal debug noise", messages)
        self.assertIn("a real warning", messages)
