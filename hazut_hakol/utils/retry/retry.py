from time import sleep
from typing import Callable, Tuple, Type

from loguru import logger


def _retry(
        func: Callable[[], None],
        *,
        max_attempts: int,
        backoff: int,
        allowed_exceptions: Tuple[Type[BaseException], ...] = (Exception,),
        step_name: str = "task pipeline"
) -> None:
    attempt = 1
    while attempt <= max_attempts:
        try:
            func()
            return
        except allowed_exceptions as exc:
            logger.warning(
                f"{step_name} failed on attempt {attempt}/{max_attempts}: {exc}"
            )
            if attempt == max_attempts:
                raise
            sleep_secs = backoff ** attempt
            logger.info(f"Retrying {step_name} after {sleep_secs:.1f}s ...")
            sleep(sleep_secs)
            attempt += 1
