"""Documentation generation"""

import os
from pathlib import Path
from typing import Union, List

import argh

from epythet.templates import (
    table_of_contents_header,
    RstTitle,
    AutoDocs,
)
from epythet.config_parser import parse_config

path_sep = os.path.sep


def gen_rst_docs_and_path(
    module_dir: Union[str, Path],
    auto_options: List[AutoDocs] = (AutoDocs.members,),
    ignore: List[str] = None,
):
    """Generates autodocs rst and rst path relative to module file structure


    >>> import epythet
    >>> from pathlib import Path
    >>> assert sorted(path for docs,
    ...     path in epythet.autogen.gen_rst_docs_and_path(Path(epythet.__file__).parent)
    ... ) == (
    ... ['epythet.rst', 'epythet/autogen.rst', 'epythet/call_make.rst',
    ... 'epythet/config_parser.rst', 'epythet/docs_gen.rst', 'epythet/setup_docsrc.rst',
    ... 'epythet/templates.rst', 'epythet/tools.rst']
    ... )

    :param module_dir: module starting dir which should be named the project name
    :param auto_options: list of automodule options to include
    :param ignore: skip file if path contains any ignore strings
    :return: rst_doc, rst_path
    """
    module_dir = Path(module_dir).absolute()
    root_name = str(module_dir)
    root_name_length = len(root_name) + 1
    module_name = module_dir.name
    init_path = path_sep + '__init__'
    for pyfile in Path(root_name).glob('**/*.py'):
        if (pyfile.parent / '__init__.py').is_file() is True and (
            not ignore or all(skip not in str(pyfile) for skip in ignore)
        ):
            with open(pyfile) as f:
                pyfile_contents = f.read()
            if len(pyfile_contents) > 0:
                module_path = os.path.join(
                    module_name, str(pyfile)[root_name_length:-3]
                ).replace(init_path, '')
                module_ref = module_path.replace(path_sep, '.')
                rst_path = module_path + '.rst'

                if '\n.. auto' in pyfile_contents:  # use rst in .py file docstring
                    rst_doc = AutoDocs.make_automodule(module_ref, options=None)
                else:  # generate auto_docs with title and auto_options
                    rst_title = RstTitle.make_title(module_ref, RstTitle.section)
                    rst_doc = rst_title + AutoDocs.make_automodule(
                        module_ref, options=auto_options
                    )
                yield rst_doc, rst_path


def make_autodocs_for_modules_files(
    module_dir: Union[str, Path],
    docsrc_dir: Union[str, Path],
    output_dirname: str,
    skip_existing=True,
    ignore: List[str] = None,
):
    """Create sphinx autodocs for module and table of contents

    :param module_dir: module starting dir
    :param output_dirname: directory name to be created under docsrc
    :param skip_existing: existing docs will not be overwritten if True
    :param docsrc_dir: path to sphinx docs source file
    :param ignore: skip file if path contains any ignore strings
    """

    base_path = docsrc_dir / output_dirname
    table_of_contents_rst_path = docsrc_dir / 'table_of_contents.rst'
    table_of_contents_rst_doc = table_of_contents_header
    toc_files = []
    for doc, path in gen_rst_docs_and_path(module_dir=module_dir, ignore=ignore):
        toc_files.append(f"   {output_dirname}/{path[:-len('.rst')]}\n")
        rst_full_path = base_path / path
        if skip_existing and rst_full_path.is_file():
            continue
        rst_full_path.parent.mkdir(parents=True, exist_ok=True)
        rst_full_path.write_text(doc)
    toc_files.sort()
    table_of_contents_rst_doc += ''.join(toc_files)
    table_of_contents_rst_path.write_text(table_of_contents_rst_doc)


@argh.arg('-i', '--ignore', nargs='*')
def make_autodocs(
    project_dir: Union[str, Path],
    output_dirname='module_docs',
    skip_existing=True,
    docsrc_dir=None,
    ignore: List[str] = None,
):
    """Create sphinx autodocs and table of contents for module defined by setup.cfg

    :param project_dir: Path to root project directory containing setup.cfg
    :param output_dirname: directory name to be created under docsrc
    :param skip_existing: existing docs will not be overwritten if True
    :param docsrc_dir: path to sphinx docs source file
    :param ignore: skip file if path contains any ignore strings
    """
    project_dir = Path(project_dir).absolute()
    project_name, _, _, _, _ = parse_config(project_dir / 'setup.cfg')
    if docsrc_dir is None:
        docsrc_dir = project_dir / 'docsrc'

    module_dir = project_dir / project_name
    make_autodocs_for_modules_files(
        module_dir=module_dir,
        docsrc_dir=docsrc_dir,
        output_dirname=output_dirname,
        skip_existing=skip_existing,
        ignore=ignore,
    )


if __name__ == '__main__':
    import argh

    argh.dispatch_command(make_autodocs)
