"""Fixture for DR011: single backticks render as italics."""


def bad_single_backticks():  # ruleid: DR011
    """A LabeledElement that uses a `dict` as the labels container."""


def good_double_backticks():  # ok: DR011
    """A LabeledElement that uses a ``dict`` as the labels container."""


def good_roles():  # ok: DR011
    """See :func:`dict` and :class:`list` and `a link <https://example.com>`_."""
