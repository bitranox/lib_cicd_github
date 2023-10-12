Changelog
=========

- new MAJOR version for incompatible API changes,
- new MINOR version for added functionality in a backwards compatible manner
- new PATCH version for backwards compatible bug fixes

v1.0.6
--------
2023-10-12:
    - do not upload codecov to codeclimate on scheduled builds

v1.0.5
--------
2023-10-09:
    - implement PyPI Upload API Token

v1.0.4
--------
2023-10-09:
    - repair scheduled run detection

v1.0.3
--------
2023-10-08:
    - do not upload codecov on scheduled builds, because of error
      'Too many uploads to this commit.' when upload codecov again and again.

v1.0.2
--------
2023-07-21:
    - create mypy cache dir '.mypy_cache'
    - require minimum python 3.8
    - remove python 3.7 tests
    - introduce PEP517 packaging standard
    - introduce pyproject.toml build-system
    - remove mypy.ini
    - remove pytest.ini
    - remove setup.cfg
    - remove setup.py
    - remove .bettercodehub.yml
    - remove .travis.yml
    - update black config
    - clean ./tests/test_cli.py
    - add codeql badge
    - move 3rd_party_stubs outside the src directory to ``./.3rd_party_stubs``
    - add pypy 3.10 tests
    - add python 3.12-dev tests

v1.0.1.2
---------
2022-06-02: update to github actions checkout@v3 and setup-python@v3

v1.0.1
--------
2022-03-29: remedy mypy Untyped decorator in cli

v1.0.0
---------
2022-03-25:
 - initial pypi release
 - update documentation and tests
 - list ./dist dir if existing

v0.0.1
---------
2021-08-23: initial release
