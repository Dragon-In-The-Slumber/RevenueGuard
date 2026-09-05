"""
Logging setup.

The codebase used bare `print()` across eight modules, which meant no levels, no
timestamps, no module names, and nothing a log aggregator could filter. Anything
that mattered — an LLM falling back to a template, a Razorpay call degrading to a
mock — was indistinguishable from the mock email bodies flooding stdout.
"""

import logging
import os
import sys

_CONFIGURED = False


def configure_logging() -> None:
    """Idempotent root-logger setup. Called once from the app lifespan."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s %(levelname)-7s %(name)-28s %(message)s",
        datefmt="%H:%M:%S",
    ))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, level, logging.INFO))

    # These are chatty at INFO and drown the agent's own output.
    for noisy in ("httpx", "httpcore", "chromadb", "urllib3", "google_genai",
                  "google.genai", "sqlalchemy.engine", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
