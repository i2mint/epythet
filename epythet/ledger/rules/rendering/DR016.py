"""Fixture for DR016: unexpected indentation became a block quote."""


def bad_indent_after_paragraph():  # ruleid: DR016
    """Do a thing.

    A paragraph that wraps
    onto a second line
        and then an indented line with no blank line before it.
    """


def good_intentional_quote():  # ok: DR016
    """Do a thing.

    A paragraph.

        An intentionally indented quote.

    Back to normal.
    """


def good_literal_block():  # ok: DR016
    """Do a thing::

        code = here
    """
