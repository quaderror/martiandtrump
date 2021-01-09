"""
"""
import logging
import os
import sys
from martiandtrump import config, streamer, system, translator, twitter, utils


CONFIG_FILE = 'config.ini'
CONSOLE_FORMAT = '%(levelname)s %(message)s'
LOG_FORMAT = '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
LOG_TYPE = 'log'
SCRIPT_DIR, SCRIPT_NAME = utils.script_meta()
TIME_FORMAT = '%Y-%m-%d %H-%M-%S,%f'


if __name__ == '__main__':

    # Load the config settings.
    config_path = os.path.join(SCRIPT_DIR, CONFIG_FILE)
    config_dict = config.config_load(config_path)

    # Configure and start logging.
    log_dir = config.config_default(config_dict, 'logs', 'directory',
                                    SCRIPT_DIR)
    log_dir = system.dir_check(log_dir, SCRIPT_DIR)
    log_type = config.config_default(config_dict, 'logs', 'type', LOG_TYPE)
    log_file = '.'.join([SCRIPT_NAME, utils.text_time(TIME_FORMAT), log_type])
    log_path = os.path.join(log_dir, log_file)
    handlers = [
        ('console', 'WARN', CONSOLE_FORMAT),
        ('stream', 'WARN', None),
        (log_path, 'INFO', LOG_FORMAT),
    ]
    log, problems = utils.log_setup(SCRIPT_NAME, handlers)
    log.info('Logging to ' + ', '.join([name for name, _, _ in handlers]))

    # Perform a straight command-line translation on any arguments.
    if len(sys.argv) > 1:
        text = ' '.join(sys.argv[1:])
        vocab = config_dict['vocab'] if 'vocab' in config_dict else {}
        result = translator.translate(text, vocab)
        print(result)
    
    # Run as a realtime twitter translator if no arguments have been supplied.
    elif system.lock(SCRIPT_NAME):
        source_id = config_dict['source']['id']
        account = dict(config_dict['account'])
        listener = dict(config_dict['listener'])
        vocab = dict(config_dict['vocab'])
        result = streamer.start(source_id, account, listener, vocab)
        system.lock_break(SCRIPT_NAME)

    # Clean up diagnostically-boring log files.
    utils.log_cleanup(log_path, problems, log)
