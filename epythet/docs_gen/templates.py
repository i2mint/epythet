from enum import Enum
from typing import Union, List


class ValueStrEnum(Enum):
    def __str__(self):
        return self.value

    @classmethod
    def has_value(cls, value: str):
        """Check of value is one of the enum values

        :param value: string or ValueStrEnum
        :return: boolean
        """
        return isinstance(value, RstTitle) or value in (item.value for item in cls)


class RstTitle(ValueStrEnum):
    """RST Title convention:

    # # with overline, for parts
    # * with overline, for chapters
    # =, for sections
    # -, for subsections
    # ^, for subsubsections
    # “, for paragraphs

    Normally, there are no heading levels assigned to certain characters as the structure is determined from the
    succession of headings. However, it is better to stick to the same convention
    """
    part = '#'
    chapter = '*'
    section = '='
    subsection = '-'
    subsubsection = '^'
    paragraphs = '"'

    @classmethod
    def has_overline(cls, title_type: Union[str, ValueStrEnum]) -> bool:
        """Check if title_type will generate a title with both over and underline

        :param title_type: one from RstTitle enum
        :return: boolean
        """
        return RstTitle(title_type) in (cls.part, cls.chapter)

    @classmethod
    def make_title(cls, text: str, title_type: Union[str, ValueStrEnum]) -> str:
        """Generate RST title

        :param text: title text
        :param title_type: one from RstTitle enum
        :return: rst title string
        """
        title_type = RstTitle(title_type)
        _title_line = str(title_type) * len(text)
        _title = f"{text}\n{_title_line}\n"
        if cls.has_overline(title_type):
            _title = f"{_title_line}\n{_title}"
        return _title


class AutoDocs(ValueStrEnum):
    """Generate automodule rst and help with options"""

    members = ":members:"

    @classmethod
    def make_automodule(cls, import_ref: str, options: List[Union[str, ValueStrEnum]] = None):
        """Generate automodule rst with options included

        :param import_ref: ref for this file is "epythet.docs_gen.templates"
        :param options: list of autodoc options, such as AutoDocs.members
        :return: rst string
        """
        automod_doc = automodule_t.format(import_ref=import_ref)
        automod_doc += '\n'
        if options:
            for op in options:
                automod_doc = f"{automod_doc}   {op}\n"
        return automod_doc


master_file_t = """\
{rst_title}

.. include:: ./table_of_contents.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
"""

master_file_title_t = "Welcome to {display_name}'s documentation!"

table_of_contents_header = """\
.. toctree::
   :maxdepth: 2
   :caption: Contents:

"""

automodule_t = ".. automodule:: {import_ref}"
