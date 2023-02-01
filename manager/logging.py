"""Standardized loggging configuration."""

import logging
from datetime import datetime


def configure_log(log="", verbose=2):
    """Configure SilverLine logging.

    Uses the same convention as the linux runtime:
        0:ERROR -> 40
        1:NOTIF -> 30
        2:INFO -> 20
        3:DEBUG -> 10
        4:TRACE -> 5
        5:ALL -> 0

    Parameters
    ----------
    log : str
        File to save log to. Will save to `{log}-{date}.log`.
    verbose : int or str
        Logging level to use (0-5; 5 is most verbose).
    """
    level = {
        0: 40, 1: 30, 2: 20, 3: 10, 4: 5, 5: 0
    }.get(verbose, 0)

    handlers = [logging.StreamHandler()]
    if log:
        handlers.append(
            logging.FileHandler("{}{}.log".format(
                log, datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))))

    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(name)s:%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers)


def __fmt(x):
    if isinstance(x, int):
        return "x{:02x}".format(x)
    elif isinstance(x, str):
        return "u{}..{}".format(x[:2], x[-4:])
    return x


def format_message(msg, *ctx) -> str:
    """Format message with context."""
    if len(ctx) == 0:
        return msg
    return "[{}] {}".format(".".join([__fmt(x) for x in ctx]), msg)
