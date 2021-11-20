
- run a command passed as string

.. code-block:: bash

    # to be used in travis.yml
    # run a command passed as string, wrap it in colored banners, retry 3 times, sleep 30 seconds when retry
    $> lib_cicd_github_cli run "description" "command -some -options" --retry=3 --sleep=30


- get the branch to work on from travis environment variables

.. code-block:: bash

    $> BRANCH=$(lib_cicd_github_cli get_branch)

python methods:

- install, jobs to do in the Travis "install" section

.. include:: ../lib_cicd_github/lib_cicd_github.py
    :code: python
    :start-after: # install{{{
    :end-before: # install}}}

- script, jobs to do in the Travis "script" section

.. include:: ../lib_cicd_github/lib_cicd_github.py
    :code: python
    :start-after: # script{{{
    :end-before: # script}}}

- after_success, jobs to do in the Travis "after_success" section

.. include:: ../lib_cicd_github/lib_cicd_github.py
    :code: python
    :start-after: # after_success{{{
    :end-before: # after_success}}}

- deploy, deploy to pypi in the Travis "after_success" section

.. include:: ../lib_cicd_github/lib_cicd_github.py
    :code: python
    :start-after: # deploy{{{
    :end-before: # deploy}}}

- get_branch, determine the branch to work on from Travis environment

.. include:: ../lib_cicd_github/lib_cicd_github.py
    :code: python
    :start-after: # get_branch{{{
    :end-before: # get_branch}}}


- run, usually used internally


.. include:: ../lib_cicd_github/lib_cicd_github.py
    :code: python
    :start-after: # run{{{
    :end-before: # run}}}

- travis.py example

.. include:: ../.travis.yml
    :code: yaml
