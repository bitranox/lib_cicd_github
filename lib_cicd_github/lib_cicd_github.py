# STDLIB
import os
import pathlib
import subprocess
import sys
import time
from typing import List

# OWN
import lib_log_utils
import cli_exit_tools

# run{{{
def run(
    description: str,
    command: str,
    retry: int = 3,
    sleep: int = 30,
    banner: bool = True,
    show_command: bool = True,
) -> None:
    """
    runs and retries a command passed as string and wrap it in "success" or "error" banners


    Parameter
    ---------
    description
        description of the action, shown in the banner
    command
        the command to launch
    retry
        retry the command n times, default = 3
    sleep
        sleep for n seconds between the commands, default = 30
    banner
        if to use banner for run/success or just colored lines.
        Errors will be always shown as banner
    show_command
        if the command is shown - take care not to reveal secrets here !


    Result
    ---------
    none


    Exceptions
    ------------
    none


    Examples
    ------------

    >>> run('test', "unknown command", sleep=0)
    Traceback (most recent call last):
        ...
    SystemExit: ...

    >>> run('test', "unknown command", sleep=0, show_command=False)
    Traceback (most recent call last):
        ...
    SystemExit: ...

    >>> run('test', "echo test")
    >>> run('test', "echo test", show_command=False)

    """
    # run}}}

    command = command.strip()
    lib_log_utils.setup_handler()

    if show_command:
        command_description = command
    else:
        command_description = "***secret***"

    lib_log_utils.banner_success(
        f"Action: {description}\nCommand: {command_description}",
        banner=banner,
    )
    tries = retry
    while True:
        try:
            subprocess.run(command, shell=True, check=True)
            lib_log_utils.banner_success(f"Success: {description}", banner=False)
            break
        except Exception as exc:
            tries = tries - 1
            # try 3 times, because sometimes connection or other errors on travis
            if tries:
                lib_log_utils.banner_notice(
                    f"Retry in {sleep} seconds: {description}\nCommand: {command_description}",
                    banner=False,
                )
                time.sleep(sleep)
            else:
                if show_command:
                    exc_message = str(exc)
                else:
                    exc_message = "Command ***secret*** returned non-zero exit status"
                lib_log_utils.banner_error(
                    f"Error: {description}\nCommand: {command_description}\n{exc_message}",
                    banner=True,
                )
                if hasattr(exc, "returncode"):
                    if exc.returncode is not None:  # type: ignore
                        sys.exit(exc.returncode)  # type: ignore
                sys.exit(1)  # pragma: no cover
        finally:
            cli_exit_tools.flush_streams()


# get_branch{{{
def get_branch() -> str:
    """
    Return the branch to work on


    Parameter
    ---------
    GITHUB_REF
        from environment

    Result
    ---------
    the branch


    Exceptions
    ------------
    none


    ============  =================================  ==========================  ==========  =======================================================
    Build         GITHUB_REF                         TRAVIS_PULL_REQUEST_BRANCH  TRAVIS_TAG  Notice
    ============  =================================  ==========================  ==========  =======================================================
    Push          refs/heads/<branch>                ---                         ---         return <branch> from GITHUB_REF

    Custom Build  <branch>                           ---                         ---         return <branch> from TRAVIS_BRANCH
    Pull Request  <master>       <branch>                    ---         return <branch> from TRAVIS_PULL_REQUEST_BRANCH
    Tagged        <tag>          ---                         <tag>       return 'master'
    ============  =============  ==========================  ==========  =======================================================

    TRAVIS_BRANCH:
        for push builds, or builds not triggered by a pull request, this is the name of the branch.
        for builds triggered by a pull request this is the name of the branch targeted by the pull request.
        for builds triggered by a tag, this is the same as the name of the tag (TRAVIS_TAG).
        Note that for tags, git does not store the branch from which a commit was tagged. (so we use always master in that case)

    TRAVIS_PULL_REQUEST_BRANCH:
        if the current job is a pull request, the name of the branch from which the PR originated.
        if the current job is a push build, this variable is empty ("").

    TRAVIS_TAG:
        If the current build is for a git tag, this variable is set to the tag’s name, otherwise it is empty ("").

    >>> # Setup
    >>> github_ref_backup = get_env_data('GITHUB_REF')

    >>> # test Master
    >>> set_env_data('GITHUB_REF', 'refs/heads/development')
    >>> assert get_branch() == 'development'

    >>> # Teardown
    >>> set_env_data('GITHUB_REF', github_ref_backup)

    """
    # get_branch}}}

    github_ref = get_env_data('GITHUB_REF')
    if github_ref:
        branch = github_ref.split('/')[-1]
    else:
        branch = "master"
    return branch


# install{{{
def install(dry_run: bool = True) -> None:
    """
    upgrades pip, setuptools, wheel and pytest-pycodestyle


    Parameter
    ---------
    cPIP
        from environment, the command to launch pip, like "python -m pip"


    Examples
    --------

    >>> if os.getenv('TRAVIS'):
    ...     install(dry_run=True)

    """
    # install}}}
    if dry_run:
        return
    pip_prefix = get_pip_prefix()
    run(
        description="install pip",
        command=" ".join([pip_prefix, "install --upgrade pip"]),
    )
    run(
        description="install setuptools",
        command=" ".join([pip_prefix, "install --upgrade setuptools"]),
    )
    run(
        description="install readme renderer",
        command=" ".join([pip_prefix, "install --upgrade readme_renderer"]),
    )

    if is_pypy3() and os_is_linux():
        # for pypy3 install rust compiler on linux to compile cryptography
        run(
            description="install rust compiler for twine",
            command="curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
        )
        os.environ["PATH"] = ":".join([os.getenv("PATH", ""), str(pathlib.Path.home() / ".cargo/bin")])

    if is_arch_s390x() or is_arch_ppc64le():
        # for s390 and ppc64le do not install rust compiler, and skip rust build -
        # because it did not work 2021-02-15, error on compiling cryptography
        os.environ["CRYPTOGRAPHY_DONT_BUILD_RUST"] = "1"

    run(
        description="install twine",
        command=" ".join([pip_prefix, "install --upgrade twine"]),
    )
    run(
        description="install wheel",
        command=" ".join([pip_prefix, "install --upgrade wheel"]),
    )
    run(
        description="install requirements",
        command=" ".join([pip_prefix, "install --upgrade -r ./requirements.txt"]),
    )
    run(
        description="install test requirements",
        command=" ".join([pip_prefix, "install --upgrade -r ./requirements_test.txt"]),
    )


# script{{{
def script(dry_run: bool = True) -> None:
    """
    travis jobs to run in travis.yml section "script":
    - run setup.py test
    - run pip with install option test
    - run pip standard install
    - test the CLI Registration
    - install the test requirements
    - install codecov
    - install pytest-codecov
    - run pytest coverage
    - run mypy strict
        - if MYPY_STRICT="True"
    - rebuild the rst files (resolve rst file includes)
        - needs RST_INCLUDE_SOURCE, RST_INCLUDE_TARGET set and BUILD_DOCS="True"
    - check if deployment would succeed, if setup.py exists and not a tagged build

    Parameter
    ---------
    cPREFIX
        from environment, the command prefix like 'wine' or ''
    cPIP
        from environment, the command to launch pip, like "python -m pip"
    cPYTHON
        from environment, the command to launch python, like 'python' or 'python3' on MacOS
    CLI_COMMAND
        from environment, must be set in travis - the CLI command to test with option --version
    MYPY_STRICT
        from environment, if pytest with mypy --strict should run
    PACKAGE_NAME
        from environment, the package name to pass to mypy
    BUILD_DOCS
        from environment, if rst file should be rebuilt
    RST_INCLUDE_SOURCE
        from environment, the rst template with rst includes to resolve
    RST_INCLUDE_TARGET
        from environment, the rst target file
    DEPLOY_WHEEL
        from environment, if a wheel should be generated
        only if setup.py exists and on non-tagged builds (there we deploy for real)
    dry_run
        if set, this returns immediately - for CLI tests


    Examples
    --------
    >>> script()

    """
    # script}}}
    if dry_run:
        return
    lib_log_utils.setup_handler()
    cli_command = os.getenv("CLI_COMMAND", "")
    command_prefix = os.getenv("cPREFIX", "")
    python_prefix = get_python_prefix()
    package_name = os.getenv("PACKAGE_NAME", "")

    if do_flake8_tests():
        run(
            description="flake8 tests",
            command=" ".join([python_prefix, "-m flake8 --statistics --benchmark"]),
        )
    else:
        lib_log_utils.banner_notice("flake8 tests disabled on this build")

    if do_mypy_tests():
        mypy_options = os.getenv("MYPY_OPTIONS", "")
        run(
            description="mypy tests",
            command=" ".join([python_prefix, "-m mypy -p", package_name, mypy_options]),
        )
    else:
        lib_log_utils.banner_notice("mypy typecheck --strict disabled on this build")

    if do_pytest():
        if do_coverage():
            option_codecov = "".join(["--cov=", package_name])
        else:
            lib_log_utils.banner_notice("coverage disabled")
            option_codecov = ""
        run(
            description="run pytest",
            command=" ".join([python_prefix, "-m pytest", option_codecov]),
        )
    else:
        lib_log_utils.banner_notice("pytest disabled")

    # run(description='setup.py test', command=' '.join([python_prefix, './setup.py test']))
    # run(description='pip install, option test', command=' '.join([pip_prefix, 'install', repository, '--install-option test']))
    # run(description='pip standard install', command=' '.join([pip_prefix, 'install', repository]))
    run(
        description="setup.py install",
        command=" ".join([python_prefix, "./setup.py install"]),
    )
    run(
        description="check CLI command",
        command=" ".join([command_prefix, cli_command, "--version"]),
    )

    if do_build_docs():
        rst_include_source = os.getenv("RST_INCLUDE_SOURCE", "")
        rst_include_target = os.getenv("RST_INCLUDE_TARGET", "")
        rst_include_source_name = pathlib.Path(rst_include_source).name
        rst_include_target_name = pathlib.Path(rst_include_target).name
        run(
            description=" ".join(
                [
                    "rst rebuild",
                    rst_include_target_name,
                    "from",
                    rst_include_source_name,
                ]
            ),
            command=" ".join(
                [
                    command_prefix,
                    "rst_include include",
                    rst_include_source,
                    rst_include_target,
                ]
            ),
        )
    else:
        lib_log_utils.banner_notice("rebuild doc file is disabled on this build")

    if do_deploy_sdist() or do_build_test():
        run(
            description="create source distribution",
            command=" ".join([python_prefix, "setup.py sdist"]),
        )
    else:
        lib_log_utils.banner_notice("create source distribution is disabled on this build")

    if do_deploy_wheel() or do_build_test():
        run(
            description="create binary distribution (wheel)",
            command=" ".join([python_prefix, "setup.py bdist_wheel"]),
        )
    else:
        lib_log_utils.banner_notice("create wheel distribution is disabled on this build")

    if do_deploy_sdist() or do_deploy_wheel() or do_build_test():
        run(
            description="check distributions",
            command=" ".join([command_prefix, "twine check dist/*"]),
        )


# after_success{{{
def after_success(dry_run: bool = True) -> None:
    """
    travis jobs to run in travis.yml section "after_success":
        - coverage report
        - codecov
        - codeclimate report upload


    Parameter
    ---------
    cPREFIX
        from environment, the command prefix like 'wine' or ''
    cPIP
        from environment, the command to launch pip, like "python -m pip"
    CC_TEST_REPORTER_ID
        from environment, must be set in travis
    TRAVIS_TEST_RESULT
        from environment, this is set by TRAVIS automatically
    dry_run
        if set, this returns immediately - for CLI tests


    Examples
    --------
    >>> after_success()

    """
    # after_success}}}

    if dry_run:
        return

    command_prefix = os.getenv("cPREFIX", "")
    pip_prefix = get_pip_prefix()

    if do_coverage():
        run(
            description="coverage report",
            command=" ".join([command_prefix, "coverage report"]),
        )
        if do_upload_codecov():
            run(
                description="coverage upload to codecov",
                command=" ".join([command_prefix, "codecov"]),
            )
        else:
            lib_log_utils.banner_notice("codecov upload disabled")

        if do_upload_code_climate() and os.getenv("CC_TEST_REPORTER_ID"):
            if os_is_windows():
                os.environ["CODECLIMATE_REPO_TOKEN"] = os.getenv("CC_TEST_REPORTER_ID", "")
                run(
                    description="install codeclimate-test-reporter",
                    command=" ".join([pip_prefix, "install codeclimate-test-reporter"]),
                )
                run(
                    description="coverage upload to codeclimate",
                    command=" ".join([command_prefix, "codeclimate-test-reporter"]),
                )
            else:
                run(
                    description="download test reporter",
                    command="curl -L https://codeclimate.com/downloads/test-reporter/test-reporter-latest-linux-amd64 > ./cc-test-reporter",
                )
                run(
                    description="test reporter set permissions",
                    banner=False,
                    command="chmod +x ./cc-test-reporter",
                )
                travis_test_result = os.getenv("TRAVIS_TEST_RESULT", "")
                run(
                    description="coverage upload to codeclimate",
                    command=" ".join(
                        [
                            "./cc-test-reporter after-build --exit-code",
                            travis_test_result,
                        ]
                    ),
                )
        else:
            lib_log_utils.banner_notice("Code Climate Coverage is disabled, no CC_TEST_REPORTER_ID")


# deploy{{{
def deploy(dry_run: bool = True) -> None:
    """
    uploads sdist and wheels to pypi on success


    Parameter
    ---------
    cPREFIX
        from environment, the command prefix like 'wine' or ''
    PYPI_PASSWORD
        from environment, passed as secure, encrypted variable to environment
    TRAVIS_TAG
        from environment, needs to be set
    DEPLOY_SDIST, DEPLOY_WHEEL
        from environment, one of it needs to be true
    dry_run
        if set, this returns immediately - for CLI tests


    Examples
    --------
    >>> deploy()

    """
    # deploy}}}

    if dry_run:
        return
    command_prefix = os.getenv("cPREFIX", "")
    github_username = get_github_username()
    pypi_password = os.getenv("PYPI_PASSWORD", "")

    if do_deploy():
        if not dry_run:  # pragma: no cover
            run(
                description="upload to pypi",
                command=" ".join(
                    [
                        command_prefix,
                        "twine upload --repository-url https://upload.pypi.org/legacy/ -u",
                        github_username,
                        "-p",
                        pypi_password,
                        "--skip-existing",
                        "dist/*",
                    ]
                ),
                show_command=False,
            )  # pragma: no cover
    else:
        lib_log_utils.banner_notice("pypi deploy is disabled on this build")


def get_pip_prefix() -> str:
    """
    get the pip_prefix including the command prefix like : 'wine python -m pip'

    >>> if 'TRAVIS' in os.environ:
    ...    discard = get_pip_prefix()

    """
    c_parts: List[str] = list()
    c_parts.append(os.getenv("cPREFIX", ""))
    c_parts.append(os.getenv("cPIP", ""))
    command_prefix = " ".join(c_parts).strip()
    return command_prefix


def get_python_prefix() -> str:
    """
    get the python_prefix including the command prefix like : 'wine python'

    >>> if 'TRAVIS' in os.environ:
    ...    discard = get_python_prefix()

    """
    c_parts: List[str] = list()
    c_parts.append(os.getenv("cPREFIX", ""))
    c_parts.append(os.getenv("cPYTHON", ""))
    python_prefix = " ".join(c_parts).strip()
    return python_prefix


def get_github_username() -> str:
    """
    get the github username like 'bitranox'

    >>> discard = get_github_username()

    """
    repo_slug = os.getenv("TRAVIS_REPO_SLUG", "")
    github_username = repo_slug.split("/")[0]
    return github_username


def do_mypy_tests() -> bool:
    """
    if mypy should be run

    Parameter
    ---------
    MYPY_DO_TESTS
        from environment

    Examples:

    >>> # Setup
    >>> save_do_mypy = os.getenv('MYPY_DO_TESTS')

    >>> # BUILD_TEST != 'True'
    >>> os.environ['MYPY_DO_TESTS'] = 'false'
    >>> assert not do_mypy_tests()

    >>> # BUILD_TEST == 'true'
    >>> os.environ['MYPY_DO_TESTS'] = 'True'
    >>> assert do_mypy_tests()

    >>> # Teardown
    >>> if save_do_mypy is None:
    ...     os.unsetenv('MYPY_DO_TESTS')
    ... else:
    ...     os.environ['MYPY_DO_TESTS'] = save_do_mypy

    """

    if os.getenv("MYPY_DO_TESTS", "").lower() == "true":
        return True
    else:
        return False


def do_pytest() -> bool:
    """
    if pytest should be run

    Parameter
    ---------
    PYTEST_DO_TESTS
        from environment

    Examples:

    >>> # Setup
    >>> save_do_pytest = os.getenv('PYTEST_DO_TESTS')

    >>> # BUILD_TEST != 'True'
    >>> os.environ['PYTEST_DO_TESTS'] = 'false'
    >>> assert not do_pytest()

    >>> # BUILD_TEST == 'true'
    >>> os.environ['PYTEST_DO_TESTS'] = 'True'
    >>> assert do_pytest()

    >>> # Teardown
    >>> if save_do_pytest is None:
    ...     os.unsetenv('PYTEST_DO_TESTS')
    ... else:
    ...     os.environ['PYTEST_DO_TESTS'] = save_do_pytest

    """
    if os.getenv("PYTEST_DO_TESTS", "").lower() == "true":
        return True
    else:
        return False


def do_coverage() -> bool:
    """
    if coverage should be run (via pytest)

    Parameter
    ---------
    DO_COVERAGE
        from environment

    Examples:

    >>> # Setup
    >>> save_do_coverage = os.getenv('DO_COVERAGE')

    >>> # BUILD_TEST != 'True'
    >>> os.environ['DO_COVERAGE'] = 'false'
    >>> assert not do_coverage()

    >>> # BUILD_TEST == 'true'
    >>> os.environ['DO_COVERAGE'] = 'True'
    >>> assert do_coverage()

    >>> # Teardown
    >>> if save_do_coverage is None:
    ...     os.unsetenv('DO_COVERAGE')
    ... else:
    ...     os.environ['DO_COVERAGE'] = save_do_coverage

    """
    if os.getenv("DO_COVERAGE", "").lower() == "true":
        return True
    else:
        return False


def do_upload_codecov() -> bool:
    """
    if code coverage should be uploaded to codecov

    Parameter
    ---------
    DO_COVERAGE_UPLOAD_CODECOV
        from environment

    Examples:

    >>> # Setup
    >>> save_upload_codecov = os.getenv('DO_COVERAGE_UPLOAD_CODECOV')

    >>> # BUILD_TEST != 'True'
    >>> os.environ['DO_COVERAGE_UPLOAD_CODECOV'] = 'false'
    >>> assert not do_upload_codecov()

    >>> # BUILD_TEST == 'true'
    >>> os.environ['DO_COVERAGE_UPLOAD_CODECOV'] = 'True'
    >>> assert do_upload_codecov()

    >>> # Teardown
    >>> if save_upload_codecov is None:
    ...     os.unsetenv('DO_COVERAGE_UPLOAD_CODECOV')
    ... else:
    ...     os.environ['DO_COVERAGE_UPLOAD_CODECOV'] = save_upload_codecov

    """
    if os.getenv("DO_COVERAGE_UPLOAD_CODECOV", "").lower() == "true":
        return True
    else:
        return False


def do_upload_code_climate() -> bool:
    """
    if code coverage should be uploaded to code climate

    Parameter
    ---------
    DO_COVERAGE_UPLOAD_CODE_CLIMATE
        from environment

    Examples:

    >>> # Setup
    >>> save_upload_code_climate = os.getenv('DO_COVERAGE_UPLOAD_CODE_CLIMATE')

    >>> # BUILD_TEST != 'True'
    >>> os.environ['DO_COVERAGE_UPLOAD_CODE_CLIMATE'] = 'false'
    >>> assert not do_upload_code_climate()

    >>> # BUILD_TEST == 'true'
    >>> os.environ['DO_COVERAGE_UPLOAD_CODE_CLIMATE'] = 'True'
    >>> assert do_upload_code_climate()

    >>> # Teardown
    >>> if save_upload_code_climate is None:
    ...     os.unsetenv('DO_COVERAGE_UPLOAD_CODE_CLIMATE')
    ... else:
    ...     os.environ['DO_COVERAGE_UPLOAD_CODE_CLIMATE'] = save_upload_code_climate

    """
    if os.getenv("DO_COVERAGE_UPLOAD_CODE_CLIMATE", "").lower() == "true":
        return True
    else:
        return False


def do_build_docs() -> bool:
    """
    if README.rst should be rebuilt

    Parameter
    ---------
    BUILD_DOCS
        from environment, "True" or "False"
    RST_INCLUDE_SOURCE
        from environment, the source template file
    RST_INCLUDE_TARGET
        from environment, the target file


    Examples:

    >>> # Setup
    >>> save_build_docs = os.getenv('BUILD_DOCS')
    >>> save_rst_include_source = os.getenv('RST_INCLUDE_SOURCE')
    >>> save_rst_include_target = os.getenv('RST_INCLUDE_TARGET')

    >>> # BUILD_DOCS != 'true'
    >>> os.environ['BUILD_DOCS'] = 'false'
    >>> os.unsetenv('RST_INCLUDE_SOURCE')
    >>> os.unsetenv('RST_INCLUDE_TARGET')
    >>> assert not do_build_docs()

    >>> # BUILD_DOCS == 'true', no source, no target
    >>> os.environ['BUILD_DOCS'] = 'True'
    >>> # no real test here, we cant set environ in travis
    >>> assert do_build_docs() is not None

    >>> # BUILD_DOCS == 'true', no source
    >>> os.environ['RST_INCLUDE_TARGET'] = 'some_target_file'
    >>> # no real test here, we cant set environ in travis
    >>> assert do_build_docs() is not None

    >>> # BUILD_DOCS == 'true', source and target
    >>> os.environ['RST_INCLUDE_SOURCE'] = 'some_source_file'
    >>> # no real test here, we cant set environ in travis
    >>> assert do_build_docs() is not None

    >>> # Teardown
    >>> if save_build_docs is None:
    ...     os.unsetenv('BUILD_DOCS')
    ... else:
    ...     os.environ['BUILD_DOCS'] = save_build_docs

    >>> if save_rst_include_source is None:
    ...     os.unsetenv('RST_INCLUDE_SOURCE')
    ... else:
    ...     os.environ['RST_INCLUDE_SOURCE'] = save_rst_include_source

    >>> if save_rst_include_target is None:
    ...     os.unsetenv('RST_INCLUDE_TARGET')
    ... else:
    ...     os.environ['RST_INCLUDE_TARGET'] = save_rst_include_target


    """
    if os.getenv("BUILD_DOCS", "").lower() != "true":
        return False

    if not os.getenv("RST_INCLUDE_SOURCE"):
        return False

    if not os.getenv("RST_INCLUDE_TARGET"):
        return False
    else:
        return True


def do_deploy_sdist() -> bool:
    """
    if we should deploy sdist


    Parameter
    ---------
    DEPLOY_SDIST
        from environment

    Examples:

    >>> # Setup
    >>> save_deploy_sdist = os.getenv('DEPLOY_SDIST')

    >>> # DEPLOY_WHEEL != 'true'
    >>> os.environ['DEPLOY_SDIST'] = 'false'
    >>> assert not do_deploy_sdist()

    >>> # DO_FLAKE8_TESTS == 'true'
    >>> os.environ['DEPLOY_SDIST'] = 'True'
    >>> assert do_deploy_sdist()

    >>> # Teardown
    >>> if save_deploy_sdist is None:
    ...     os.unsetenv('DEPLOY_SDIST')
    ... else:
    ...     os.environ['DEPLOY_SDIST'] = save_deploy_sdist

    """

    if os.getenv("DEPLOY_SDIST", "").lower() == "true":
        return True
    else:
        return False


def do_deploy_wheel() -> bool:
    """
    if we should deploy wheels

    Parameter
    ---------
    DEPLOY_WHEEL
        from environment

    Examples:

    >>> # Setup
    >>> save_deploy_wheel = os.getenv('DEPLOY_WHEEL')

    >>> # DEPLOY_WHEEL != 'true'
    >>> os.environ['DEPLOY_WHEEL'] = 'false'
    >>> assert not do_deploy_wheel()

    >>> # DO_FLAKE8_TESTS == 'true'
    >>> os.environ['DEPLOY_WHEEL'] = 'True'
    >>> assert do_deploy_wheel()

    >>> # Teardown
    >>> if save_deploy_wheel is None:
    ...     os.unsetenv('DEPLOY_WHEEL')
    ... else:
    ...     os.environ['DEPLOY_WHEEL'] = save_deploy_wheel

    """

    if os.getenv("DEPLOY_WHEEL", "").lower() == "true":
        return True
    else:
        return False


def do_flake8_tests() -> bool:
    """
    if we should do flake8 tests

    Parameter
    ---------
    DO_FLAKE8_TESTS
        from environment

    Examples:

    >>> # Setup
    >>> save_flake8_test = os.getenv('DO_FLAKE8_TESTS')

    >>> # DO_FLAKE8_TESTS != 'true'
    >>> os.environ['DO_FLAKE8_TESTS'] = 'false'
    >>> assert not do_flake8_tests()

    >>> # DO_FLAKE8_TESTS == 'true'
    >>> os.environ['DO_FLAKE8_TESTS'] = 'True'
    >>> assert do_flake8_tests()

    >>> # Teardown
    >>> if save_flake8_test is None:
    ...     os.unsetenv('DO_FLAKE8_TESTS')
    ... else:
    ...     os.environ['DO_FLAKE8_TESTS'] = save_flake8_test



    """
    if os.getenv("DO_FLAKE8_TESTS", "").lower() == "true":
        return True
    else:
        return False


def do_build_test() -> bool:
    """
    if a build should be created for test purposes

    Parameter
    ---------
    BUILD_TEST
        from environment

    Examples:

    >>> # Setup
    >>> save_build_test = os.getenv('BUILD_TEST')

    >>> # BUILD_TEST != 'True'
    >>> os.environ['BUILD_TEST'] = 'false'
    >>> assert not do_build_test()

    >>> # BUILD_TEST == 'true'
    >>> os.environ['BUILD_TEST'] = 'True'
    >>> assert do_build_test()

    >>> # Teardown
    >>> if save_build_test is None:
    ...     os.unsetenv('BUILD_TEST')
    ... else:
    ...     os.environ['BUILD_TEST'] = save_build_test

    """
    if os.getenv("BUILD_TEST", "").lower() == "true":
        return True
    else:
        return False


def is_pypy3() -> bool:
    """
    if it is a travis pypy3 build

    Parameter
    ---------
    TRAVIS_PYTHON_VERSION
        from environment

    Examples:

    >>> # Setup
    >>> save_python_version = os.getenv('TRAVIS_PYTHON_VERSION')

    >>> # Test
    >>> os.environ['TRAVIS_PYTHON_VERSION'] = 'pypy3'
    >>> assert is_pypy3()

    >>> os.environ['TRAVIS_PYTHON_VERSION'] = '3.9'
    >>> assert not is_pypy3()

    >>> # Teardown
    >>> if save_python_version is None:
    ...     os.unsetenv('TRAVIS_PYTHON_VERSION')
    ... else:
    ...     os.environ['TRAVIS_PYTHON_VERSION'] = save_python_version

    """
    if os.getenv("TRAVIS_PYTHON_VERSION", "").lower() == "pypy3":
        return True
    else:
        return False


def is_arch_s390x() -> bool:
    """
    if it is a travis s390x cpu architecture
    Parameter
    ---------
    TRAVIS_CPU_ARCH
        from environment

    Examples:

    >>> # Setup
    >>> save_cpu_arch = os.getenv('TRAVIS_CPU_ARCH')

    >>> # Test
    >>> os.environ['TRAVIS_CPU_ARCH'] = 's390x'
    >>> assert is_arch_s390x()

    >>> os.environ['TRAVIS_CPU_ARCH'] = 'amd64'
    >>> assert not is_arch_s390x()

    >>> # Teardown
    >>> if save_cpu_arch is None:
    ...     os.unsetenv('TRAVIS_CPU_ARCH')
    ... else:
    ...     os.environ['TRAVIS_CPU_ARCH'] = save_cpu_arch

    """
    if os.getenv("TRAVIS_CPU_ARCH", "").lower() == "s390x":
        return True
    else:
        return False


def is_arch_ppc64le() -> bool:
    """
    if it is a travis ppc64le cpu architecture
    Parameter
    ---------
    TRAVIS_CPU_ARCH
        from environment

    Examples:

    >>> # Setup
    >>> save_cpu_arch = os.getenv('TRAVIS_CPU_ARCH')

    >>> # Test
    >>> os.environ['TRAVIS_CPU_ARCH'] = 'ppc64le'
    >>> assert is_arch_ppc64le()

    >>> os.environ['TRAVIS_CPU_ARCH'] = 'amd64'
    >>> assert not is_arch_ppc64le()

    >>> # Teardown
    >>> if save_cpu_arch is None:
    ...     os.unsetenv('TRAVIS_CPU_ARCH')
    ... else:
    ...     os.environ['TRAVIS_CPU_ARCH'] = save_cpu_arch

    """
    if os.getenv("TRAVIS_CPU_ARCH", "").lower() == "ppc64le":
        return True
    else:
        return False


def os_is_windows() -> bool:
    """
    if it is a travis windows build

    Parameter
    ---------
    TRAVIS_OS_NAME
        from environment

    Examples:

    >>> # Setup
    >>> save_travis_os_name = os.getenv('TRAVIS_OS_NAME')

    >>> # TRAVIS_OS_NAME == 'linux'
    >>> os.environ['TRAVIS_OS_NAME'] = 'linux'
    >>> assert not os_is_windows()

    >>> # TRAVIS_OS_NAME == 'windows'
    >>> os.environ['TRAVIS_OS_NAME'] = 'windows'
    >>> assert os_is_windows()

    >>> # Teardown
    >>> if save_travis_os_name is None:
    ...     os.unsetenv('TRAVIS_OS_NAME')
    ... else:
    ...     os.environ['TRAVIS_OS_NAME'] = save_travis_os_name


    """
    if os.getenv("TRAVIS_OS_NAME", "").lower() == "windows":
        return True
    else:
        return False


def os_is_linux() -> bool:
    """
    if it is a travis linux build

    Parameter
    ---------
    TRAVIS_OS_NAME
        from environment

    Examples:

    >>> # Setup
    >>> save_travis_os_name = os.getenv('TRAVIS_OS_NAME')

    >>> # TRAVIS_OS_NAME == 'linux'
    >>> os.environ['TRAVIS_OS_NAME'] = 'linux'
    >>> assert os_is_linux()

    >>> # TRAVIS_OS_NAME == 'windows'
    >>> os.environ['TRAVIS_OS_NAME'] = 'windows'
    >>> assert not os_is_linux()

    >>> # Teardown
    >>> if save_travis_os_name is None:
    ...     os.unsetenv('TRAVIS_OS_NAME')
    ... else:
    ...     os.environ['TRAVIS_OS_NAME'] = save_travis_os_name


    """
    if os.getenv("TRAVIS_OS_NAME", "").lower() == "linux":
        return True
    else:
        return False


def do_deploy() -> bool:
    """
    if we should deploy
    if (DEPLOY_SDIST  or DEPLOY_WHEEL) and TRAVIS_TAG

    Parameter
    ---------
    DEPLOY_SDIST
        from environment
    DEPLOY_WHEEL
        from environment
    TRAVIS_TAG
        from environment

    Examples:

    >>> # Setup
    >>> save_travis_tag = os.getenv('TRAVIS_TAG')
    >>> save_deploy_sdist = os.getenv('DEPLOY_SDIST')
    >>> save_deploy_wheel = os.getenv('DEPLOY_WHEEL')

    >>> # no Tagged Commit
    >>> os.unsetenv('TRAVIS_TAG')
    >>> # no real test here, we cant set environ in travis
    >>> assert do_deploy() is not None

    >>> # Tagged Commit, DEPLOY_SDIST, DEPLOY_WHEEL != True
    >>> os.environ['TRAVIS_TAG'] = 'SOME_TAG'
    >>> os.unsetenv('DEPLOY_SDIST')
    >>> os.unsetenv('DEPLOY_WHEEL')
    >>> # no real test here, we cant set environ in travis
    >>> assert do_deploy() is not None

    >>> # Tagged Commit, DEPLOY_SDIST == True
    >>> os.environ['DEPLOY_SDIST'] = 'True'
    >>> # no real test here, we cant set environ in travis
    >>> assert do_deploy() is not None

    >>> # Teardown
    >>> if save_travis_tag is None:
    ...     os.unsetenv('TRAVIS_TAG')
    ... else:
    ...     os.environ['TRAVIS_TAG'] = save_travis_tag

    >>> if save_deploy_sdist is None:
    ...     os.unsetenv('DEPLOY_SDIST')
    ... else:
    ...     os.environ['DEPLOY_SDIST'] = save_deploy_sdist

    >>> if save_deploy_wheel is None:
    ...     os.unsetenv('DEPLOY_WHEEL')
    ... else:
    ...     os.environ['DEPLOY_WHEEL'] = save_deploy_wheel

    """
    if not os.getenv("TRAVIS_TAG"):
        return False
    if do_deploy_sdist() or do_deploy_wheel():
        return True
    else:
        return False


def get_env_data(env_variable: str) -> str:
    """
    >>> # Setup
    >>> save_mypy_path = get_env_data('MYPYPATH')

    >>> # Test
    >>> set_env_data('MYPYPATH', 'some_test')
    >>> assert get_env_data('MYPYPATH') == 'some_test'

    >>> # Teardown
    >>> set_env_data('MYPYPATH', save_mypy_path)

    """
    if env_variable in os.environ:
        env_data = os.environ[env_variable]
    else:
        env_data = ''
    return env_data


def set_env_data(env_variable: str, env_str: str) -> None:
    os.environ[env_variable] = env_str


if __name__ == "__main__":
    print(
        b'this is a library only, the executable is named "lib_travis_cli.py"',
        file=sys.stderr,
    )
