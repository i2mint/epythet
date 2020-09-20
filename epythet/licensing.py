from epythet import licenses_json_path
import json


def license_body(license=None, search_name_and_spdx_id=True, refresh=False):
    _license_info = license_info(license, search_name_and_spdx_id, refresh=refresh)
    if _license_info is not None:
        return _license_info['body']


def license_info(license=None, search_name_and_spdx_id=True, refresh=False):
    licenses = licenses_dict(refresh=refresh)
    if license not in licenses:
        if search_name_and_spdx_id:
            for ll in licenses.values():
                if license in {ll['name'], ll['spdx_id']}:
                    return ll
        print("That's not a valid license key. Here is a list of valid license keys:")
        print('\t', *licenses, sep='\n\t')
    else:
        return licenses[license]


def licenses_dict(refresh=False):
    licenses = get_licenses(refresh=refresh)
    return {x['key']: x for x in licenses}


def get_licenses(refresh=False):
    if refresh:
        try:
            licenses = get_licenses_from_github()
            json.dump(licenses, open(licenses_json_path, 'w'))
        except Exception:
            raise

    return json.load(open(licenses_json_path, 'r'))


def get_licenses_from_github():
    """get_licenses_json_from_github
    You need to have a github token placed in the right place for this!
    See pygithub for details.
    ```
    license_jsons = get_licenses_json_from_github()
    ```
    """

    from github import Github

    def gen():
        g = Github()
        license_getter = g.get_licenses()
        i = 0
        while True:
            more = license_getter.get_page(i)
            i += 1
            if len(more) > 0:
                yield more
            else:
                break

    from itertools import chain

    licenses = list(chain.from_iterable(gen()))
    licenses = [ll.raw_data for ll in licenses]
    return licenses
