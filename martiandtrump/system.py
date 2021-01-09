"""
"""
import datetime
import json
import logging
import os
import psutil
import subprocess
import sys
from martiandtrump import utils


SCRIPT_DIR, SCRIPT_NAME = utils.script_meta()
system_log = logging.getLogger(SCRIPT_NAME + '.system')


def cache_file(cache_type):
    """"""
    return os.path.join(SCRIPT_DIR, 'cache', cache_type + '.json')


def cache_read(cache_type, default=None):
    """Read a JSON cache file and return the stored dictionary."""
    cache = cache_file(cache_type)
    try:
        with open(cache, 'r') as handle:
            data = json.load(handle)
        system_log.info('Cache read OK: ' + cache)
        return data
    except (IOError, json.decoder.JSONDecodeError) as e:
        system_log.error('Cache read failed: ' + str(e))
        return default


def cache_write(cache_type, payload, clobber=False):
    """Write a JSON cache file and return True/False based on success."""
    cache = cache_file(cache_type)
    directory, name, _ = path_parts(cache)
    directory_proper = dir_check(directory, SCRIPT_DIR)
    cache = directory_proper + cache[len(directory):]
    success, text = (False, 'Cache write failed: ' + cache + ' (unsafe)')
    lock_name = '-'.join([cache_type, 'cache'])
    ready = clobber or not os.path.exists(cache)
    if lock(lock_name) and ready:
    
        # Write the cache file and log success.
        try:
            with open(cache, 'w') as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
            lock_break(lock_name)
            system_log.debug('Cache written OK: ' + cache)
            return True

        # Log an errors which occurred during the cahe write.
        except IOError as e:
            system_log.error('Cache write failed: ' + str(e))
            return False


def command_run(command):
    """Return exit code, shell output, and timedelta running a command."""
    system_log.debug('Running command: ' + command)

    # Run the command and return interesting outputs.
    began = datetime.datetime.now()
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    output = process.communicate()
    output = output[0].decode(sys.stdin.encoding, 'replace').strip()
    exit_code = process.returncode
    took = datetime.datetime.now() - began

    # Log the command result and return the interesting outputs.
    system_log.debug('Finished command: ' + command)
    system_log.debug('Command exited ' + str(exit_code))
    system_log.debug('Command took ' + str(took))
    return (exit_code, output, took)


def dir_check(directory, default):
    """Return a consist directory path, or use a default if it's missing."""
    system_log.info('Checking directory ' + directory)

    # Trim off any trailing directory separators.
    if directory.endswith(os.sep):
        directory = directory.rstrip(os.sep)

    # Make relative paths absolute, assuming they're relative to the default.
    if not directory.startswith(os.sep):
        directory = os.path.join(default, directory)
        system_log.debug('Relative directory made absolute: ' + directory)

    # If the directory doesn't exist, use the default instead.
    if not os.path.isdir(directory):
        system_log.warn('Directory not found: ' + directory)
    if not os.path.isdir(directory) and not dir_make(directory):
        directory = default
        system_log.warn('Directory changed to ' + default)

    # Return the directory determined.
    return directory


def dir_make(path):
    """Quickly make a whole directory path, not just the leaf directory."""
    try:
        os.makedirs(path, exist_ok=True)
        system_log.info('Directory created: ' + path)
    except OSError as e:
        system_log.error('Directory not created: ' + path + ' (' + str(e) + ')')
        pass
    return os.path.isdir(path)


def dir_prune(path):
    """Remove as many empty directories from a given path as possible."""
    parts = path.split(os.sep)
    paths = [os.path.join(os.sep, *parts[:-x]) for x in range(1, len(parts))]
    system_log.info('Directory pruning: ' + path)
    try:
        _ = [os.rmdir(path) for path in paths]
    except OSError as e:
        system_log.debug('Directory pruning finished: ' + str(e))
        pass
    return True


def lock(lock_name):
    """Determine a named process lock file and create it."""
    lock = lock_path(lock_name)
    my_pid = str(os.getpid())
    lock_pid = None

    # If the lock exists, get the PID in it.
    if os.path.isfile(lock):
        system_log.debug('Lock ' + lock + ' exists, checking PID')
        try:
            with open(lock, 'r') as handle:
                lock_pid = handle.read().strip()
        except IOError as e:
            system_log.warn("Couldn't read " + lock + ': ' + str(e))

    # If the PID is stale, break the lock.
    if lock_pid and not psutil.pid_exists(int(lock_pid)):
        lock_break(lock_name)

    # If the lock exists, return False.
    if os.path.isfile(lock):
        system_log.info('Lock ' + lock + ' preventing ' + lock_name)
        return False

    # Try to create a lock, write the current PID in it, and return True.
    try:
        with open(lock, 'w') as handle:
            handle.write(my_pid)
        system_log.info(' '.join(['Lock', lock, 'created for PID', my_pid]))
        return True

    # Report any problems creating the lock file.
    except IOError as e:
        system_log.error(' '.join(["Couldn't create", lock, ':', str(e)]))
        return False


def lock_break(lock_name):
    """Determine a named process lock file and remove it."""
    lock = lock_path(lock_name)

    # Try to remove the lock file and report success.
    try:
        if os.path.exists(lock):
            os.unlink(lock)
        system_log.info('Unlocked ' + lock)
        return True

    # Report any problems removing the lock file.
    except OSError:
        system_log.warn("Couldn't unlock " + lock)
        return False


def lock_multi(lock_names, create):
    """Affect multiple named process locks quickly, tidying up failures."""
    system_log.info('Affecting multiple locks: ' + ', '.join(lock_names))
    todo = lock if create else lock_break

    # Iterate over each lock to affect.
    for lock_name in lock_names:
        success = todo(lock_name)
        if not success and create:
            message = ' '.join(['Problem with', lock_name, 'lock, reverting'])
            system_log.error(message)
            lock_multi(lock_names, False)
        if not success:
            return False

    # Return True if everything went according to plan.
    return True


def lock_path(lock_name):
    """Determine the path for a file to lock a named process."""
    lock_file = '.'.join(['', lock_name, 'pid'])
    lock_path = os.path.join(SCRIPT_DIR, lock_file)
    system_log.debug(' '.join(['Lock for', lock_name, 'is', lock_path]))
    return lock_path


def path_parts(filepath):
    """Split a filepath into its directories, name, and extension."""
    path = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    name, extension = os.path.splitext(filename)

    # Format the values for output
    extension = None if extension == '' else extension[1:]
    result = (path, name, extension)

    # Log result and return it.
    system_log.debug('Filepath ' + filepath + ' parts: ' + str(result))
    return result


def power(state=None):
    """"""
    return power_set(state) if state else power_get()


def power_get():
    """"""
    default = {
        'state': 'OK',
        'time': datetime.datetime.utcnow(),
    }
    power = cache_read('power', [dict(default)])
    power = power[-1] if isinstance(power, list) and len(power) else default
    power = {
        'state': power.get('state', default['state']),
        'time': power.get('time', default['time'])
    }
    power['text'], power['since'] = utils.text_fromstamp(power['time'])
    system_log.info('Power gotten as ' + str(power))
    return power


def power_set(state):
    """"""
    now = {
        'state': str(state),
        'time': datetime.datetime.utcnow().timestamp(),
    }
    report = system_log.info if state == 'OK' else system_log.warn
    report('Power set to ' + now['state'])
    cache = cache_read('power', [])
    cache.append(dict(now))
    return cache_write('power', cache, clobber=True)


def service_change(service, verb):
    """Control a system service stopping, starting, or restarting it."""
    system_log.info('Service change request: ' + service + ' ' + verb)

    # Check the verb is a valid thing to do to a service.
    if verb not in ['restart', 'start', 'stop']:
        system_log.error("Can't make a service " + verb)
        return False

    # Compile the command. Requires sudoers file entry to run.
    arguments = {'service': service, 'verb': verb}
    command = 'sudo /usr/sbin/service {service} {verb}'
    command = command.format(**arguments)

    # Only run the command if a service lock can be obtained.
    lock_name = '_'.join(['service', service])
    if not lock(lock_name):
        return False
    exit_code, output, took = command_run(command)
    lock_break(lock_name)

    # Report the result of trying to change the service state.
    success = exit_code == 0
    report = system_log.debug if success else system_log.error
    report(' '.join(['Service', service, verb, 'OK' if success else 'failed']))
    return success


def services_change(services, verb):
    """Control multiple services stopping, starting, or restarting them."""
    if isinstance(services, str):
        services = services.strip().split()
    message = 'Services with change requests: ' + ', '.join(services)
    system_log.info(message)

    # Iterate over each service, returning False on the first failure.
    for service in services:
        if not service_change(service, verb):
            system_log.error("Couldn't make services " + verb + ', check logs')
            return False

    # Report the result of trying to change the services states.
    system_log.info('Services made to ' + verb + ' successfully')
    return True
