"""Fixture for DR009: directive text shown as prose."""


def bad_inline_directive():  # ruleid: DR009
    """Do a thing.

    Use .. code-block:: python to show code.
    """


def bad_directive_glued_to_prose():  # ruleid: DR009
    """Tools to provide meta-interfaces of python objects.
    .. seealso:: some/other/module.py
    """


def good_directive():  # ok: DR009
    """Do a thing.

    .. note::

        Something to note.
    """
