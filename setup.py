name = 'epythet'
root_url = 'https://github.com/i2mint'
# version = '0.0.1'

more_setup_kwargs = dict(
    install_requires=[

    ],
    description="Tools for documentation and packaging.",
    keywords=['data', 'data access', 'data preperation', 'machine learning', 'artificial intelligence'],
    author='Otosense',
    license='Apache Software License',
    # download_url='{root_url}/{name}/archive/v{version}.zip'),
)

import os
from pip_packaging import next_version_for_package
from setuptools import setup

# name = os.path.split(os.path.dirname(__file__))[-1]

# current_version = current_pypi_version(name)
version = next_version_for_package(name)


def readme():
    try:
        with open('README.md') as f:
            return f.read()
    except:
        return ""


ujoin = lambda *args: '/'.join(args)

if root_url.endswith('/'):
    root_url = root_url[:-1]


def my_setup(print_params=True, **setup_kwargs):
    from setuptools import setup
    if print_params:
        import json
        print("Setup params -------------------------------------------------------")
        print(json.dumps(setup_kwargs, indent=2))
        print("--------------------------------------------------------------------")
    setup(**setup_kwargs)


dflt_kwargs = dict(
    name=f"{name}",
    version=f'{version}',
    url=f"{root_url}/{name}",
    include_package_data=True,
    platforms='any',
    long_description=readme(),
    long_description_content_type="text/markdown",

)

setup_kwargs = dict(dflt_kwargs, **more_setup_kwargs)

my_setup(**setup_kwargs)
