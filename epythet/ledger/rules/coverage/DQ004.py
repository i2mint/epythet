"""Fixture for DQ004: parameter description only restates the type."""


def retry(n: int, delay: float):  # ruleid: DQ004
    """Retry.

    :param n: an integer
    :param delay: the delay
    """


def retry_well(n: int, delay: float):  # ok: DQ004
    """Retry.

    :param n: how many attempts before giving up
    :param delay: seconds between attempts
    """
