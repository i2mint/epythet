"""Fixture for DR006: Markdown fence collapsed into an inline literal."""


def bad_python_fence():  # ruleid: DR006
    """Do a thing.

    ```python
    result = f(1)
    ```
    """


def bad_mermaid_fence():  # ruleid: DR006
    """Do a thing.

    ```mermaid
    graph TD; A-->B;
    ```
    """


def good_code_block():  # ok: DR006
    """Do a thing.

    .. code-block:: python

        result = f(1)
    """


def good_literal_block():  # ok: DR006
    """Do a thing::

        result = f(1)
    """


def good_double_backticks():  # ok: DR006
    """Do a thing with ``x`` and ``y``."""
