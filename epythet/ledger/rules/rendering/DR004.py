"""Fixture for DR004: Markdown link left literal."""


def bad_markdown_link():  # ruleid: DR004
    """See [the docs](https://example.com/docs) for details."""


def good_rst_link():  # ok: DR004
    """See `the docs <https://example.com/docs>`_ for details."""


def good_indexing_in_prose():  # ok: DR004
    """Index with [0] and call f(x); brackets alone are fine."""
