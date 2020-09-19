import re
from typing import Mapping, Union, Iterable, Generator


# TODO: postprocess_ini_section_items and preprocess_ini_section_items: Add comma separated possibility?
# TODO: Find out if configparse has an option to do this processing alreadys
def postprocess_ini_section_items(items: Union[Mapping, Iterable]) -> Generator:
    r"""Transform newline-separated string values into actual list of strings (assuming that intent)

    >>> section_from_ini = {
    ...     'name': 'aspyre',
    ...     'keywords': '\n\tdocumentation\n\tpackaging\n\tpublishing'
    ... }
    >>> section_for_python = dict(postprocess_ini_section_items(section_from_ini))
    >>> section_for_python
    {'name': 'aspyre', 'keywords': ['documentation', 'packaging', 'publishing']}

    """
    splitter_re = re.compile('[\n\r\t]+')
    if isinstance(items, Mapping):
        items = items.items()
    for k, v in items:
        if v.startswith('\n'):
            v = splitter_re.split(v[1:])
            v = [vv.strip() for vv in v if vv.strip()]
        yield k, v


# TODO: Find out if configparse has an option to do this processing alreadys
def preprocess_ini_section_items(items: Union[Mapping, Iterable]) -> Generator:
    """Transform list values into newline-separated strings, in view of writing the value to a ini formatted section
    >>> section = {
    ...     'name': 'aspyre',
    ...     'keywords': ['documentation', 'packaging', 'publishing']
    ... }
    >>> for_ini = dict(preprocess_ini_section_items(section))
    >>> print('keywords =' + for_ini['keywords'])  # doctest: +NORMALIZE_WHITESPACE
    keywords =
        documentation
        packaging
        publishing

    """
    if isinstance(items, Mapping):
        items = items.items()
    for k, v in items:
        if isinstance(v, list):
            v = '\n\t' + '\n\t'.join(v)
        yield k, v


def mk_replacer_from_dict(from_to_dict):
    """
    >>> r = mk_replacer_from_dict({'is': 'are', 'life': 'butterflies'})
    >>> r("There is no life in the void.")
    'There are no butterflies in the void.'
    """
    p = re.compile('|'.join(map(r'({})'.format, map(re.escape, from_to_dict.keys()))))
    f = lambda x: from_to_dict[x.group(0)]

    def replacer(s):
        return p.sub(f, s)

    return replacer


fc = dict(
    reset="\033[0m",  # alias for reset_all
    reset_all="\033[0m",

    bold="\033[1m",
    dim="\033[2m",
    underlined="\033[4m",
    blink="\033[5m",
    reverse="\033[7m",
    hidden="\033[8m",
    reset_bold="\033[21m",
    reset_dim="\033[22m",
    reset_underlined="\033[24m",
    reset_blink="\033[25m",
    reset_reverse="\033[27m",
    reset_hidden="\033[28m",

    default="\033[39m",

    black="\033[30m",
    red="\033[31m",
    green="\033[32m",
    yellow="\033[33m",
    blue="\033[34m",
    magenta="\033[35m",
    cyan="\033[36m",
    gray="\033[37m",

    dark_gray="\033[90m",
    dark_red="\033[91m",
    dark_green="\033[92m",
    dark_yellow="\033[93m",
    dark_blue="\033[94m",
    dark_magenta="\033[95m",
    dark_cyan="\033[96m",

    white="\033[97m",

    background_default="\033[49m",

    background_black="\033[40m",
    background_red="\033[41m",
    background_green="\033[42m",
    background_yellow="\033[43m",
    background_blue="\033[44m",
    background_magenta="\033[45m",
    background_cyan="\033[46m",
    background_gray="\033[47m",

    background_dark_gray="\033[100m",
    background_dark_red="\033[101m",
    background_dark_green="\033[102m",
    background_dark_yellow="\033[103m",
    background_dark_blue="\033[104m",
    background_dark_magenta="\033[105m",
    background_dark_cyan="\033[106m",

    background_white="\033[107m",
)

try:
    from py2store.sources import DictAttr

    fc = DictAttr(**fc)
except ModuleNotFoundError:
    pass  # DictAttr is convenient, but not necessary


def highlight(string, effect=fc['reverse'], beg_mark='[[', end_mark=']]', end_effect=fc['reset_all']):
    r"""Interprets a string's highlight markers to be able to make highlights in the string.

    This is meant for very simple situations. A more powerful and fast function could be made by
    using regular expressions and a map to map "codes" to "effects".

    Try this:

    >>> print(highlight("This is [[the section]] that is [[highlighted]]."))  # doctest:+SKIP

    Above, "reverse" is used as the default effect.
    But You can change that to bold blue ink on yellow background. That's three effects:
    1 (for bold), 34, for the blue foreground (ink), and 43 for the "yellow" (more like brown)
    background (paper).

    >>> my_string = "This is [[the section]] that is [[highlighted]]."
    >>> print(highlight(my_string, "\033[1;34;43m"))  # doctest:+SKIP

    \033[whaaaa?!? Yeah... well, either you do it that has-no-life-outside-unicode way.
    If so, Ansi help you!
    See [this wiki section](https://en.wikipedia.org/wiki/ANSI_escape_code#SGR_parameters).
    or [this tutorial](https://www.lihaoyi.com/post/BuildyourownCommandLinewithANSIescapecodes.html#rich-text).

    If not, we've prepared a map between human language and effect codes in the form of the
    `fc` variable of this module. It's a dict (and if you have ``py2store``, it's a mapping containing
    that dict and allowing you access through attributes too).

    >>> from epythet.util import fc
    >>> list(fc)[20:25]
    ['magenta', 'cyan', 'gray', 'dark_gray', 'dark_red']

    :param string: String with highlight formatting
    :param effect: The effect to use for the highlighting (some unicode like "\033[21m")
    :param beg_mark: String that marks the beginning of the highlight
    :param end_mark: String that marks the end of the highlight
    :param end_effect: The unicode to use to reset the effect
    :return:
    """
    return string.replace(beg_mark, effect).replace(end_mark, end_effect)
