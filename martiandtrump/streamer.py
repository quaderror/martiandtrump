"""
"""
import logging
import tweepy
from martiandtrump import translator, twitter, utils


SCRIPT_DIR, SCRIPT_NAME = utils.script_meta()
stream_log = logging.getLogger(SCRIPT_NAME + '.streamer')


def start(source_id, tweeting_config, listener_config=None, vocab={}):
    """Handle authentication and startup of the streaming translator."""
    stream_log.debug('Stream starting')
    try:
        # Handle authentication of tweeting and listening accounts.
        tweeting_auth = twitter.authenticate(**tweeting_config)
        listener_auth = tweeting_auth
        if listener_config:
            listener_auth = twitter.authenticate(**listener_config)
            # TODO; handle errors gracefully.

        # Prepare and run the real-time streamer, filtering on the source_id.
        translator = StreamTranslator(tweeting_auth, source_id, vocab)
        thisStream = tweepy.Stream(listener_auth, translator)
        thisStream.filter(follow=[source_id])
        return True

    # Catch and log any exceptions occurring during streamer startup and run.
    except Exception as error:
        stream_log.error('Streamer error: ' + str(error))
        return False


class StreamTranslator(tweepy.StreamListener):
    """
    """

    def __init__(self, tweeting_auth, source_id, vocab):
        """Log the stream initializing and apply arguments to self."""
        stream_log.debug('Stream initializing')
        tweepy.StreamListener.__init__(self)
        self.account = tweepy.API(tweeting_auth)
        self.source_id = int(source_id)
        self.vocab = vocab

    def on_data(self, event):
        """Respond to events returned by the stream."""
        this = twitter.parse(event, only=[self.source_id])
        action_needed = this and this['user_id'] == self.source_id

        # Respond to any tweets or tweet quotations.
        if action_needed and this['type'] in ['tweet', 'quoted_tweet']:
            translation = translator.translate(this['body'], self.vocab)
            twitter.tweet(self.account, translation)

        # Retweet the same retweets.
#        if action_needed and this['type'] == 'retweet':
#            twitter.retweet(self.account, this['body_id'])

    def on_error(self, error):
        """Capture and log any stream errors."""
        stream_log.error('Stream error: ' + str(error))
        # Let tweepy handle 420 throttling behaviour.
