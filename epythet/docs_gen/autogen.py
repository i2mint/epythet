import os
from pathlib import Path

from epythet.docs_gen.templates import table_of_contents_header, RstTitle, AutoDocs
from epythet.pack_util import read_configs, DFLT_CONFIG_FILE
from py2store.filesys import FileCollection
from py2store.trans import filtered_iter
from typing import Union, List
from types import ModuleType

path_sep = os.path.sep


def gen_rst_docs_and_path(module: Union[ModuleType, str], auto_options: List[AutoDocs] = (AutoDocs.members,)):
    """Generates autodocs rst and rst path relative to module file structure
        TODO: use epythet.docs_gen.templates.AutoDocs

    :param module: module or import name
    :param auto_options: list of automodule options to include
    :return: rst_doc, rst_path
    """
    if isinstance(module, str):
        module = __import__(module)
    root_name = os.path.dirname(module.__file__)
    root_name_length = len(root_name) + 1
    module_name = module.__name__
    init_path = path_sep + '__init__'
    for pyfile in filtered_iter(lambda x: x.endswith('.py'))(FileCollection(root_name)):
        with open(pyfile) as f:
            pyfile_contents = f.read()
        if len(pyfile_contents) == 0:
            continue

        module_path = os.path.join(module_name, pyfile[root_name_length:-3]).replace(init_path, '')
        module_ref = module_path.replace(path_sep, '.')
        rst_path = module_path + '.rst'

        if '\n.. auto' in pyfile_contents:  # use rst in .py file docstring
            rst_doc = AutoDocs.make_automodule(module_ref, options=None)
        else:  # generate auto_docs with title and auto_options
            rst_title = RstTitle.make_title(module_ref, RstTitle.section)
            rst_doc = rst_title + AutoDocs.make_automodule(module_ref, options=auto_options)
        yield rst_doc, rst_path


def make_autodocs_for_modules_files(module: Union[ModuleType, str], output_dirname='module_docs',
                                    skip_existing=True, docsrc_dir=None):
    """Create sphinx autodocs for module and table of contents

    :param module: module or import name
    :param output_dirname: directory name to be created under docsrc
    :param skip_existing: existing docs will not be overwritten if True
    :param docsrc_dir: path to sphinx docs source file
    """
    if not docsrc_dir:
        if isinstance(module, str):
            module = __import__(module)
        docsrc_dir = Path(module.__file__).absolute().parent.parent / 'docsrc'
    base_path = docsrc_dir / output_dirname
    table_of_contents_rst_path = docsrc_dir / 'table_of_contents.rst'
    table_of_contents_rst_doc = table_of_contents_header
    toc_files = []
    for doc, path in gen_rst_docs_and_path(module):
        toc_files.append(f"   {output_dirname}/{path[:-len('.rst')]}\n")
        rst_full_path = base_path / path
        if skip_existing and rst_full_path.is_file():
            continue
        rst_full_path.parent.mkdir(parents=True, exist_ok=True)
        rst_full_path.write_text(doc)
    toc_files.sort()
    table_of_contents_rst_doc += ''.join(toc_files)
    table_of_contents_rst_path.write_text(table_of_contents_rst_doc)


def make_autodocs(project_dir, output_dirname='module_docs', skip_existing=True, docsrc_dir=None):
    """Create sphinx autodocs and table of contents for module defined by setup.cfg

    :param project_dir: Path to root project directory containing setup.cfg
    :param output_dirname: directory name to be created under docsrc
    :param skip_existing: existing docs will not be overwritten if True
    :param docsrc_dir: path to sphinx docs source file
    """
    config = read_configs(Path(project_dir) / DFLT_CONFIG_FILE)
    make_autodocs_for_modules_files(module=config['name'], output_dirname=output_dirname,
                                    skip_existing=skip_existing, docsrc_dir=docsrc_dir)


if __name__ == "__main__":
    import argh

    argh.dispatch_command(make_autodocs)
