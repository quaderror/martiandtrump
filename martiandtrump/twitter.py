"""
"""
import html
import json
import logging
import random
import time
import tweepy
from martiandtrump import utils


SCRIPT_DIR, SCRIPT_NAME = utils.script_meta()
twitter_log = logging.getLogger(SCRIPT_NAME + '.twitter')


def authenticate(consumer_key, consumer_secret, access_key, access_secret):
    """Return an authenticated OAuth handler for interacting with Twitter."""
    twitter_log.debug('Authenticating with Twitter')
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_key, access_secret)
    return auth


def parse(payload, only=[], exclude=[]):
    """Attempt to parse a twitter event payload based on known structures."""
    payload = payload.strip()
    payload = json.loads(payload)

    # Tests to perform on the payload, and corresponding parser functions.
    tests = [
        ('delete', parse_delete),
        ('direct_message', parse_direct_message),
        ('event', parse_event),
        ('friends', parse_friends),
        ('retweeted_status', parse_retweet),
        ('text', parse_tweet),
    ]

    # Perform each test on the payload until an appropriate parser is found.
    for test, parser in tests:
        parsed = False
        if not payload.get(test):
            continue

        # Parse the event payload and log according to only/exclude args.
        parsed = parser(payload)
        user_id = parsed['user_id']

        log_only = only and user_id in only
        log_excluded = not only and user_id not in exclude
        if log_only or log_excluded:
            twitter_log.debug('Parsing Twitter event: ' + str(payload))
            twitter_log.debug('Parsed Twitter event: ' + str(parsed))
        return parsed

    # Log any parsing failures.
    twitter_log.warn('Parsing twitter event failed: ' + str(payload))
    return False


def parse_body(payload):
    """Simplify getting the full, unabridged text of a given event payload."""
    fulltext = payload.get('extended_tweet', {}).get('full_text')
    body = fulltext if fulltext else payload['text']
    return html.unescape(body)


def parse_delete(payload):
    """Parse the event payload of a Twitter status deletion."""
    return {
        'body': None,
        'body_id': payload['delete']['status']['id'],
        'type': 'delete',
        'user': None,
        'user_id': payload['delete']['status']['user_id'],
    }


def parse_direct_message(payload):
    """Parse the event payload of a Twitter direct message."""
    return {
        'body': payload['direct_message']['text'],
        'body_id': payload['direct_message']['id'],
        'type': 'direct_message',
        'user': payload['direct_message']['sender_screen_name'],
        'user_id': payload['direct_message']['sender_id'],
    }


def parse_event(payload):
    """Parse the event payload of a self-describing Twitter event."""
    return {
        'body': payload['target_object']['text'],
        'body_id': payload['target_object']['id'],
        'type': payload.get('event'),
        'user': payload['source']['screen_name'],
        'user_id': payload['source']['id'],
    }


def parse_friends(payload):
    """Parse the werid friends list that happens on users timelines."""
    return {
        'body': None,
        'body_id': None,
        'type': 'friends',
        'user': None,
        'user_id': None,
    }


def parse_retweet(payload):
    """Parse the event payload of a Twitter retweet."""
    return {
        'body': parse_body(payload),
        'body_id': payload['id'],
        'type': 'retweet',
        'user': payload['user']['screen_name'],
        'user_id': payload['user']['id'],
    }


def parse_tweet(payload):
    """Parse the event payload of a regular Twitter tweet."""
    return {
        'body': parse_body(payload),
        'body_id': payload['id'],
        'type': 'tweet',
        'user': payload['user']['screen_name'],
        'user_id': payload['user']['id'],
    }


def retweet(connection, tweet_id):
    """Use a twitter connection to retweet a supplied tweet ID."""
    # Attempt to retweet the given tweet ID and return True on success.
    try:
        connection.retweet(tweet_id)
        twitter_log.debug('Retweet ID ' + tweet_id + ' OK')
        return True

    # In the event an error occurred, log it and return False.
    except tweepy.TweepError as error:
        twitter_log.error('Retweet ID ' + tweet_id + ' failed: ' + str(error))
        return False


def tweet(connection, body, reply_to=None, delay=0, delay_variance=None):
    """Use a twitter connection to post a tweet with optional reply/delay."""
    if isinstance(connection, dict):
        connection = authenticate(**connection)
    if isinstance(connection, tweepy.auth.OAuthHandler):
        connection = tweepy.API(connection)
    body = random.choice(body) if isinstance(body, list) else str(body)

    # Handle any requested delay in posting.
    if delay and delay_variance:
        delay = int(delay)
        delay_variance = int(delay_variance)
        delay_min = delay - delay_variance
        delay_max = delay + delay_variance
        delay = random.randint(delay_min, delay_max)
    if delay and delay > 0:
        twitter_log.debug('Tweet delayed by ' + str(delay))
        time.sleep(delay)

    # Attempt to tweet the given payload and return True on success.
    try:
        connection.update_status(status=body, in_reply_to_status_id=reply_to)
        twitter_log.info('Tweet posted successfully: ' + body)
        return True

    # In the event an error occurred, log it and return False.
    except tweepy.TweepError as error:
        twitter_log.error('Tweet posting failed: ' + str(error))
        return False

