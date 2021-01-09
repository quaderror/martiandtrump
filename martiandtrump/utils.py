"""
"""
import datetime
import io
import logging
import __main__ as main
import os
import time


# This has to come first so logging works properly.
def script_meta():
    """Return the path and name of the main python script."""
    path = os.path.abspath(os.path.dirname(main.__file__))
    name = os.path.basename(main.__file__).rsplit('.', 1)[0]
    return path, name


SCRIPT_PATH, SCRIPT_NAME = script_meta()
utils_log = logging.getLogger(SCRIPT_NAME + '.utils')


def log_cleanup(log_path, stream, logger=None):
    """Clean up a log file if an important log stream is empty."""
    cleanup = True if stream.getvalue() == '' else False
    stream.close()
    if cleanup is True and logger is not None:
        logger.info('Logging found no problems, cleaning ' + log_path)
    if cleanup is True:
        os.remove(log_path)
    return os.path.exists(log_path)


def log_setup(name=__name__, handlers=[], logger=None):
    """Return a logger object and optional stream with a bunch of handlers."""
    stream = False
    if logger is None:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

    # Loop over triplets describing required handlers.
    for handle, level, formatting in handlers:
        handler = None

        # Prepare different types of log handlers.
        if handle == 'console':
            handler = logging.StreamHandler()
        elif handle == 'stream':
            stream = io.StringIO()
            handler = logging.StreamHandler(stream)
        else:
            handler = logging.FileHandler(handle, mode='w')  # TODO: safen?

        # Prepare log level filtering.
        if level:
            level = logging.getLevelName(level)
            handler.setLevel(level)

        # Prepare optional log formatting.
        if formatting:
            formatter = logging.Formatter(formatting)
            handler.setFormatter(formatter)

        # Add handler to the logger.
        logger.addHandler(handler)

    # Return the configured logger, and a single optional log stream.
    return (logger, stream)


def string_bounded(text, prefix, suffix):
    """Return the first substring in a string bounded by prefix and suffix."""
    try:
        start = text.index(prefix) + len(prefix)
        finish = text.index(suffix, start)
        return text[start:finish], text[finish:]
    except ValueError:
        return None, text


def strings_bounded(text, prefix, suffix):
    """Return all substrings in a string bounded by prefix and suffix."""
    matches = []
    match = True
    while match:
        match, text = string_bounded(text, prefix, suffix)
        if match:
            matches.append(match)
    return matches


def text_since(seconds):
    """Humanize a period of time in seconds into a descriptive string."""
    try:
        seconds = int(seconds)
    except ValueError:
        return 'unknown'
    if seconds < 2:
        return 'now'
    units = dict([
        (604800, 'weeks'),
        (86400, 'days'),
        (3600, 'hours'),
        (60, 'minutes'),
        (1, 'seconds'),
    ])
    for period in sorted(units, reverse=True):
        number = int(seconds / int(period))
        if number > 1:
            humanized = str(number) + ' ' + units[period]
            break
    utils_log.debug('Humanized ' + str(seconds) + ' into ' + humanized)
    return humanized


def text_time(time_format='%Y-%m-%d %H-%M-%S', stamp=None):
    """Return a string for the current time, formatted as required."""

    # Get the current time and format it into a string.
    if stamp is None:
        stamp = time.time()
    dt = datetime.datetime.fromtimestamp(stamp)
    text = dt.strftime(time_format)

    # Log the result and return the string.
    utils_log.debug('Made time_string: ' + text)
    return text


def text_fromstamp(stamp):
    """"""
    dt = datetime.datetime.fromtimestamp(int(stamp))
    since = datetime.datetime.utcnow() - dt
    return text_time(stamp=stamp), text_since(since.total_seconds())
