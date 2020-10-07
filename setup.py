from setuptools import setup, find_packages


def text_of_readme_md_file():
    try:
        with open('README.md') as f:
            return f.read()
    except:
        return ""


setup(
    long_description=text_of_readme_md_file(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    entry_points={'console_scripts': ['epythet=epythet:main']})  # Note: Everything should be in the local setup.cfg
