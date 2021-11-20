.. code-block::

   Usage: lib_cicd_github [OPTIONS] COMMAND [ARGS]...

     CI/CD (Continuous Integration / Continuous Delivery) - utils for github
     actions

   Options:
     --version                     Show the version and exit.
     --traceback / --no-traceback  return traceback information on cli
     -h, --help                    Show this message and exit.

   Commands:
     after_success  coverage reports
     deploy         deploy on pypi
     get_branch     get the branch to work on
     info           get program informations
     install        updates pip, setuptools, wheel, pytest-pycodestyle
     run            run string command wrapped in run/success/error banners
     script         updates pip, setuptools, wheel, pytest-pycodestyle
