import os
import signal
from loguru import logger

_is_shutting_down = False


def main_handle_sigterm(signum, frame):
    global _is_shutting_down
    if _is_shutting_down:
        return
    _is_shutting_down = True

    logger.info(f"Main process received SIGTERM - Sending SIGTERM to all process group {os.getpgid(0)}")
