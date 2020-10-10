"""Utils to package and publish.



The typical sequence of the methodic and paranoid could be something like this:

```
python pack.py current-configs  # see what you got
python pack.py increment-configs-version  # update (increment the version and write that in setup.cfg
python pack.py current-configs-version  # see that it worked
python pack.py current-configs  # ... if you really want to see the whole configs again (you're really paranoid)
python pack.py run-setup  # see that it worked
python pack.py twine-upload-dist  # publish
# and then go check things work...
```


If you're crazy (or know what you're doing) just do

```
python pack.py go
```


"""

from wads.pack import *

argh_kwargs = {
    'namespace': 'pack',
    'functions': [
        current_configs,
        increment_configs_version,
        current_configs_version,
        twine_upload_dist,
        read_and_resolve_setup_configs,
        update_setup_cfg,
        go,
        get_name_from_configs,
        run_setup,
        current_pypi_version,
        validate_pkg_dir
    ],
    'namespace_kwargs': {
        'title': 'Package Configurations',
        'description': 'Utils to package and publish.'
    }
}

if __name__ == '__main__':
    import argh  # pip install argh

    argh.dispatch_commands(argh_kwargs.get('functions', None))
