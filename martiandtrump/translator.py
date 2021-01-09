"""
"""
import logging
import re
import requests
from martiandtrump import utils


SCRIPT_DIR, SCRIPT_NAME = utils.script_meta()
translate_log = logging.getLogger(SCRIPT_NAME + '.translator')


def case_mimic(token, example):
    """Attempt to replicate the spirit of an example's capitalization."""
    if example == example.upper() and len(example) > 1:
        return token.upper()
    if example[0] == example[0].upper():
        return token[0].upper() + token[1:]
    return token.lower()


def deduplicate_tokens(tokens, limit=280):
    """Attempt to prune repeating tokens as conservatively as possible."""
    text = ''.join(tokens)
    length = len(text)
    excess = length - limit
    if excess < 0:
        return tokens

    # If the text is too long, let's find chains of duplicated token pairs.
    duplicates = []
    idx = 0
    salvageable_chars = 0
    search = list(tokens)
    while search:

        # Move on if there's no search space or duplication.
        if len(search) < 4:
            break
        if search[:2] != search[2:4]:
            search.pop(0)
            idx = idx + 1
            continue

        # Found a duplicate, keep searching until the chain stops.
        duplicated = []
        while search[:2] == search[2:4]:
            unit = ''.join(search[:2])
            salvage = len(unit)
            duplicated.append((idx, salvage))
            salvageable_chars = salvageable_chars + salvage
            search = search[2:]
            idx = idx + 2
        duplicates.append(duplicated)

    message = 'Token deduplication can salvage ' + str(salvageable_chars)
    translate_log.debug(message)

    # If salvage won't be enough, deduplicate everything to reduce deletions.
    if length - salvageable_chars >= limit:
        duplicates = [idx for chain in duplicates for idx, _ in chain]

    # If we don't have to salvage everything, do as little as possible.
    else:
        # Interleave the lists of duplicates to prune evenly.
        longest = max(len(x) for x in duplicates)
        duplicates = [x + [None] * (longest - len(x)) for x in duplicates]
        duplicates = [x for y in zip(*duplicates) for x in y if x]

        # Loop over interleaved duplicates, stop when it'll be short enough.
        salvage = [0, 0]
        while salvage[1] <= excess:
            salvage[1] += duplicates[salvage[0]][1]  # Total salvaged.
            salvage[0] += 1  # Last idx tuple to salvage.
        duplicates = sorted([idx for idx, _ in duplicates[:salvage[0]]])
        translate_log.debug('Token deduplication salvaged ' + str(salvage[1]))

    # Remove the identified duplicates from the list of tokens.
    modifier = 0
    for idx in duplicates:
        idx -= modifier
        del tokens[idx:idx + 2]
        modifier += 2

    # Report and return the list of deduplicated tokens
    translate_log.warn('Tokens deduplicated to: ' + ''.join(tokens))
    return tokens


def delete_tokens(tokens, limit=280, changes={}):
    """Attempt to remove tokens as little as possible."""
    text = ''.join(tokens)
    length = len(text)
    excess = length - limit
    if excess < 0:
        return tokens
    translate_log.debug('Tokens will be deleted to salvage ' + str(excess))

    # Get a list of translated tokens, sorted by size from small to large.
    expendable = [v for k, v in changes.items() if v == v.lower()]
    expendable = [x for x in expendable if x == x.strip(".,'-")]
    expendable = sorted(expendable, key=len)

    # Remove pairs of expendable tokens until no excess remains.
    offset = 0
    while excess > 1:
        victim = expendable.pop(0)
        idx = tokens[offset:].index(victim)
        if idx != 0 and tokens[idx - 1] == ' ':
            idx = idx - 1
        idx = idx + offset
        victims = tokens[idx:idx + 2]
        del tokens[idx:idx + 2]
        translate_log.debug('Tokens deleted: <' + '> <'.join(victims) + '>')
        salvaged = len(''.join(victims))
        excess = excess - salvaged
        translate_log.debug('Token deletion salvaged ' + str(salvaged))
        offset = idx

    # Report and return the list of condensed tokens
    translate_log.warn('Tokens deleted to: ' + ''.join(tokens))
    return tokens


def syllables(token):
    """Return the probable number of syllables in a supplied token."""
    # Full disclosure: I can't remember where I found this, sorry.
    # It was way back in the day when I used Perl every day in my job.
    # It's been updated, mutated, ruined, and refactored beyond memory since.
    # I was young, naive, and mostly drunk.
    translate_log.debug('Syllable guessing for token: <' + token + '>')

    # Uncountable tokens have simple results returned quickly.
    if token.strip() == '':
        translate_log.debug('Token is whitespace, no syllables')
        return 0
    if len(token) < 2:
        translate_log.debug('Token is short, 1 syllable')
        return 1

    # Make token consistent for testing.
    test = token.lower()
    test = test.replace("'", '')
    test = test.rstrip('e')

    # The number of syllables is usually the number of consonant groups.
    consonant_groups = re.split('[^aeiouy]+', test)
    consonant_groups = filter(None, consonant_groups)
    consonant_groups = list(consonant_groups)
    result = len(consonant_groups)
    translate_log.debug('Token consonant groups: ' + str(result))

    # Some edge-cases affect the number of syllables further.
    for case, modifier in syllables_edgecases():
        if re.match(case, test):
            translate_log.debug('Token edge-case: ' + case + ' ' + str(modifier))
            result += modifier

    # Report and return guessed number of syllables.
    if result < 1:
        result = 1
    translate_log.debug('Token <' + token + '> syllables: ' + str(result))
    return result


def syllables_edgecases():
    """Return a list of tuples for edge-case matching and score modifiers."""
    return [
        # Edge-cases which add a syllable.
        ('[aeiou]{3}', 1),
        ('([^aeiouy])\1l$', 1),
        ('[aeiouym]bl$', 1),
        ('^coa[dglx].', 1),
        ('dien', 1),
        ('dnt$', 1),
        ('[^gq]ua[^auieo]', 1),
        ('ia', 1),
        ('ii', 1),
        ('io', 1),
        ('ism$', 1),
        ('iu', 1),
        ('[^l]lien', 1),
        ('^mc', 1),
        ('riet', 1),
        # Edge-cases which subtract a syllable.
        ('cial', -1),
        ('cious', -1),
        ('cius', -1),
        ('.ely$', -1),
        ('giu', -1),
        ('ion', -1),
        ('iou', -1),
        ('sia$', -1),
        ('tia', -1),
    ]


def syllables_repeat(string, repeat='ack'):
    """Repeat a string for the same number of syllables as a given token."""
    return repeat * syllables(string)


def tokenize(text):
    """Return a list of words and whitespaces from a given text string."""
    tokens = re.findall('\S+|\s+', text)
    translate_log.debug('Tokenized: ' + '<' + '>, <'.join(tokens) + '>')
    return tokens


def translatable(token):
    """Return True or False depending on if the token needs translation."""
    # Unusual whitespace shouldn't be affected.
    if token.isspace() and token != ' ':
        translate_log.debug('Token <' + token + '> is atypical whitespace.')
        return False

    # Punctuation or unexpected characters should be left as is.
    if token.lower() == token.upper():
        translate_log.debug('Token <' + token + '> has ambiguous case.')
        return False

    # Mentions shouldn't be translated.
    if token.startswith('@') or token.startswith('.@'):
        translate_log.debug('Token <' + token + '> is a mention.')
        return False

    # Hashtags shouldn't be translated.
    if token.startswith('#'):
        translate_log.debug('Token <' + token + '> is a hashtag.')
        return False

    # Links can't be translated.
    if token.startswith('http'):
        translate_log.debug('Token <' + token + '> is a link.')
        return True  # Covid-19 Hack
        return False

    # Initials shouldn't be translated.
    if token.endswith('.') and len(token) == 2:
        translate_log.debug('Token <' + token + '> is an initial.')
        return False

    # For everything else, there's Mastercard.
    translate_log.debug('Token <' + token + '> can be translated.')
    return True


def translate(text, vocab={}, limit=280):
    """Return a string of translated text, retaining original whitespace."""
    translate_log.info('Translating: ' + text)
    text = text.replace('http', ' http')  # Sometimes he forgets to use spaces.

    # Tokenize the text and determine unique translations.
    tokens = tokenize(text)
    unique = set(tokens)
    new = {x: translate_token(x, vocab) for x in unique if translatable(x)}
    new = {x: new[x] for x in new if new[x] != x}  # Keep only differences.
    new_tokens = [new[x] if x in new else x for x in tokens]

    # Enforce a limit on the translation length.
    new_tokens = deduplicate_tokens(new_tokens, limit)
    new_tokens = delete_tokens(new_tokens, limit, new)

    # Report and return the translation made from joining the tokens.
    translation = ''.join(new_tokens)
    translate_log.info('Translation: ' + translation)
    return translation


def translate_token(token, vocab={}):
    """Translate a token string based on a vocab dictionary or syllables."""
    translated = False
    if token.upper() == token.lower():
        translated = token

    # Attempt to rewrite propaganda links.
    if not translated and token.startswith('https://'):
        translated = translate_url(token)

    # Attempt to find the token in translation vocab.
    if not translated:
        lookup = token.lower()
    if not translated and lookup in vocab:
        translate_log.debug('Translating <' + token + '> from vocab')
        translated = case_mimic(vocab[lookup], token)

    # Attempt to find subsets of the token in translation vocab.
    if not translated:
        parts = re.findall('[A-Za-z]{2,}|.', token)
    if not translated and len(parts) > 1:
        translate_log.debug('Translating <' + token + '> by splitting')
        parts = [translate_token(x, vocab) for x in parts]
        translated = ''.join(parts)

    # Resort to deriving a translation based on syllables and plurality.
    if not translated:
        generated = syllables_repeat(token)
    if not translated and token[-1] in ['s', 'z', 'y']:
        generated = generated + token[-1]  # TODO: add 'ed'
    if not translated:
        translate_log.debug('Translating <' + token + '> by generation')
        translated = case_mimic(generated, token)

    # Report and return the token's translation.
    message = 'Token <' + token + '> translated to <' + translated + '>'
    translate_log.debug(message)
    return translated


def translate_url(url):
    """"""
    translate_log.debug('Checking <' + url + '>  for redirects')
    url = requests.get(url).url
    translate_log.debug('URL resolved as ' + url)

    if url.startswith('https://vote'):
        return 'https://joebiden.com/voter-guide/'  # lol

    return url
