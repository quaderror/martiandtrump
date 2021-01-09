"""
"""
import configparser
import logging
from martiandtrump import utils


SCRIPT_DIR, SCRIPT_NAME = utils.script_meta()
config_log = logging.getLogger(SCRIPT_NAME + '.config')


def choices(config, section, key):
    """"""
    items = config_default(config, section, key, '')
    items = items.split("\n")
    items = filter(None, items)
    return list(items)


def config_default(config, section, key, fallback=None):
    """Return a value for a section and key in a config .ini file."""
    value = config.get(section, key, fallback='')
    return fallback if value == '' else value


def config_load(filepath):
    """Load the values in a config .ini file, or exit if an error happens."""
    config = configparser.ConfigParser()

    # Try to read the config file.
    try:
        config_log.info('Reading config: ' + filepath)
        config.read_file(open(filepath))
        return config

    # Exit gracefully on error, logging the failure.
    except (FileNotFoundError, configparser.Error) as e:
        config_log.error("Couldn't read config: " + str(e))
        raise SystemExit()
