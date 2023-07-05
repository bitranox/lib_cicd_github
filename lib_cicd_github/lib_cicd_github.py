# STDLIB
from functools import lru_cache
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
                lib_log_utils.banner_spam(
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
            try:
                # on Windows under github actions we have got "ValueError: underlying buffer has been detached"
                cli_exit_tools.flush_streams()
            except ValueError:
                pass


# get_branch{{{
@lru_cache(maxsize=None)
def get_branch() -> str:
    """
    Returns the branch to work on :
        <branch>    for push, pull requests, merge
        'release'   for tagged releases


    Parameter
    ---------
    github.ref, github.head_ref, github.event_name, github.job
        from environment

    Result
    ---------
    the branch


    Exceptions
    ------------
    none


    ==============  ===================  ===================  ===================  ===================
    Build           github.ref           github.head_ref      github.event_name    github.job
    ==============  ===================  ===================  ===================  ===================
    Push            refs/heads/<branch>  ---                  push                 build
    Custom Build    refs/heads/<branch>  ---                  push                 build
    Pull Request    refs/pull/xx/merge   <branch>             pull_request         build
    Merge           refs/heads/<branch>  ---                  push                 build
    Publish Tagged  refs/tags/<tag>      ---                  release              build
    ==============  ===================  ===================  ===================  ===================

    >>> # Setup
    >>> github_ref_backup = get_env_data('GITHUB_REF')
    >>> github_head_ref_backup = get_env_data('GITHUB_HEAD_REF')
    >>> github_event_name_backup = get_env_data('GITHUB_EVENT_NAME')
    >>> clear_all_caches()

    >>> # test Push
    >>> set_env_data('GITHUB_REF', 'refs/heads/development')
    >>> set_env_data('GITHUB_HEAD_REF', '')
    >>> set_env_data('GITHUB_EVENT_NAME', 'push')
    >>> assert get_branch() == 'development'
    >>> clear_all_caches()

    >>> # test Push without github.ref
    >>> set_env_data('GITHUB_REF', '')
    >>> set_env_data('GITHUB_HEAD_REF', '')
    >>> set_env_data('GITHUB_EVENT_NAME', 'push')
    >>> assert get_branch() == 'unknown branch, event=push'
    >>> clear_all_caches()

    >>> # test PR
    >>> set_env_data('GITHUB_REF', 'refs/pull/xx/merge')
    >>> set_env_data('GITHUB_HEAD_REF', 'master')
    >>> set_env_data('GITHUB_EVENT_NAME', 'pull_request')
    >>> assert get_branch() == 'master'
    >>> clear_all_caches()

    >>> # test Publish
    >>> set_env_data('GITHUB_REF', 'refs/tags/v1.1.15')
    >>> set_env_data('GITHUB_HEAD_REF', '')
    >>> set_env_data('GITHUB_EVENT_NAME', 'release')
    >>> assert get_branch() == 'release'
    >>> clear_all_caches()

    >>> # test unknown event_name
    >>> set_env_data('GITHUB_REF', '')
    >>> set_env_data('GITHUB_HEAD_REF', '')
    >>> set_env_data('GITHUB_EVENT_NAME', 'unknown_event')
    >>> assert get_branch() == 'unknown branch, event=unknown_event'
    >>> clear_all_caches()

    >>> # Teardown
    >>> set_env_data('GITHUB_REF', github_ref_backup)
    >>> set_env_data('GITHUB_HEAD_REF', github_head_ref_backup)
    >>> set_env_data('GITHUB_EVENT_NAME', github_event_name_backup)
    >>> clear_all_caches()

    """
    # get_branch}}}

    github_ref = get_env_data("GITHUB_REF")
    github_head_ref = get_env_data("GITHUB_HEAD_REF")
    github_event_name = get_env_data("GITHUB_EVENT_NAME")

    if github_event_name == "pull_request":
        branch = github_head_ref
    elif github_event_name == "release":
        branch = "release"
    elif github_event_name == "push":
        if github_ref:
            branch = github_ref.split("/")[-1]
        else:
            branch = f"unknown branch, event={github_event_name}"
    else:
        branch = f"unknown branch, event={github_event_name}"
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

    >>> # Setup
    >>> clear_all_caches()
    >>> # Test
    >>> if is_github_actions_active():
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

    if do_setup_py_test():
        run(
            description="install package in editable(develop) mode",
            command=" ".join([pip_prefix, "install --editable .[test]"]),
        )
    elif do_setup_py():
        run(
            description="install package",
            command=" ".join([pip_prefix, "install ."]),
        )
    else:
        lib_log_utils.banner_spam("package will be not installed")


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
    >>> # setup
    >>> clear_all_caches()
    >>> # test
    >>> script()

    """
    # script}}}
    if dry_run:
        return
    lib_log_utils.setup_handler()
    command_prefix = get_env_data("cPREFIX")
    package_name = get_env_data("PACKAGE_NAME")
    python_prefix = get_python_prefix()
    pip_prefix = get_pip_prefix()

    if do_flake8_tests():
        run(description="flake8 tests", command=f"{python_prefix} -m flake8 --statistics --benchmark")
    else:
        lib_log_utils.banner_spam("flake8 tests disabled on this build")

    if do_mypy_tests():
        mypy_options = get_env_data("MYPY_OPTIONS")
        run(description="mypy tests", command=f"{python_prefix} -m mypy -p {package_name} {mypy_options}")
    else:
        lib_log_utils.banner_spam("mypy tests disabled on this build")

    if do_pytest():
        if do_coverage():
            option_codecov = f"--cov={package_name}"
        else:
            lib_log_utils.banner_spam("coverage disabled on this build")
            option_codecov = ""
        run(description="run pytest", command=f"{python_prefix} -m pytest {option_codecov}")
    else:
        lib_log_utils.banner_spam("pytest disabled on this build")

    if do_check_cli():
        cli_command = get_env_data("CLI_COMMAND")
        run(description="check CLI command", command=f"{command_prefix} {cli_command} --version")

    if do_build_docs():
        rst_include_source = os.getenv("RST_INCLUDE_SOURCE", "")
        rst_include_target = os.getenv("RST_INCLUDE_TARGET", "")
        rst_include_source_name = pathlib.Path(rst_include_source).name
        rst_include_target_name = pathlib.Path(rst_include_target).name
        run(
            description=f"rst rebuild {rst_include_target_name} from {rst_include_source_name}",
            command=f"{command_prefix} rst_include include {rst_include_source} {rst_include_target}",
        )
    else:
        lib_log_utils.banner_spam("rebuild doc file is disabled on this build")

    if do_build() or do_build_test():
        run(
            description="upgrade building system",
            command=" ".join([pip_prefix, "install --upgrade build"]),
        )

        run(
            description="upgrade twine",
            command=" ".join([pip_prefix, "install --upgrade twine"]),
        )

        run(
            description="build wheel and sdist",
            command=" ".join([python_prefix, "-m build"]),
        )

        run(
            description="check distributions",
            command=" ".join([python_prefix, "-m twine check dist/*"]),
        )

        list_dist_directory()


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
    >>> # setup
    >>> clear_all_caches()
    >>> # test
    >>> after_success()

    """
    # after_success}}}

    if dry_run:
        return

    command_prefix = get_env_data("cPREFIX")
    cc_test_reporter_id = get_env_data("CC_TEST_REPORTER_ID").strip()

    if do_coverage():
        run(description="coverage report", command=f"{command_prefix} coverage report")

        if do_upload_codecov():
            run(description="coverage upload to codecov", command=f"{command_prefix} codecov")
        else:
            lib_log_utils.banner_spam("codecov upload disabled")

        if do_upload_code_climate() and cc_test_reporter_id:
            if is_ci_runner_os_macos() or is_ci_runner_os_linux():
                download_code_climate_test_reporter_on_linux_or_macos()
                upload_code_climate_test_report_on_linux_or_macos()
            elif is_ci_runner_os_windows():
                lib_log_utils.banner_warning('Code Climate: no working "codeclimate-test-reporter" for Windows available, Nov. 2021')
            else:
                lib_log_utils.banner_warning("Code Climate Coverage - unknown RUNNER_OS ")
        else:
            lib_log_utils.banner_spam("Code Climate Coverage is disabled, no CC_TEST_REPORTER_ID")


def download_code_climate_test_reporter_on_linux_or_macos() -> None:
    download_link = ""
    if is_ci_runner_os_macos():
        download_link = "https://codeclimate.com/downloads/test-reporter/test-reporter-latest-darwin-amd64"
    elif is_ci_runner_os_linux():
        download_link = "https://codeclimate.com/downloads/test-reporter/test-reporter-latest-linux-amd64"
    else:
        lib_log_utils.banner_warning("Code Climate Coverage - unknown RUNNER_OS ")

    run(
        description="download code climate test reporter",
        command=f"curl -L {download_link} > ./cc-test-reporter",
    )
    run(
        description="set permissions for code climate test reporter",
        banner=False,
        command="chmod +x ./cc-test-reporter",
    )


def upload_code_climate_test_report_on_linux_or_macos() -> None:
    # Test Exit Code is always zero here, since the previous step on github actions completed without error
    test_exit_code = 0
    cc_test_reporter_id = get_env_data("CC_TEST_REPORTER_ID").strip()
    run(
        description="code climate test report upload",
        command=f"./cc-test-reporter after-build --exit-code {test_exit_code} --id {cc_test_reporter_id}",
    )


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
    DEPLOY_SDIST, DEPLOY_WHEEL
        from environment, one of it needs to be true
    dry_run
        if set, this returns immediately - for CLI tests


    Examples
    --------
    >>> # setup
    >>> clear_all_caches()
    >>> # test
    >>> deploy()

    """
    # deploy}}}

    if dry_run:
        return
    pypi_password = get_env_data("PYPI_PASSWORD").strip()
    if not pypi_password:
        lib_log_utils.banner_warning("can not deploy, because secret PYPI_PASSWORD is missing")
    elif do_deploy():
        if not dry_run:  # pragma: no cover
            run(
                description="upload to pypi",
                command=" ".join(
                    [
                        get_python_prefix(),
                        "-m twine upload --repository-url https://upload.pypi.org/legacy/ -u",
                        get_github_username(),
                        "-p",
                        pypi_password,
                        "--skip-existing",
                        "dist/*",
                    ]
                ),
                show_command=False,
            )  # pragma: no cover
    else:
        lib_log_utils.banner_spam("pypi deploy is disabled on this build")


'''
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

'''

'''
        run(
            description="check distributions",
            command=" ".join([python_prefix, "-m twine check dist/*"]),
        )

'''


def list_dist_directory() -> None:
    """dir the dist directory if exists"""
    command_prefix = get_env_data("cPREFIX")
    if pathlib.Path("./dist").is_dir():
        run(description="list ./dist directory", command=f"{command_prefix} ls -l ./dist")
    else:
        lib_log_utils.banner_warning('no "./dist" directory found')


@lru_cache(maxsize=None)
def get_pip_prefix() -> str:
    """
    get the pip_prefix including the command prefix like : 'wine python -m pip'

    >>> # setup
    >>> clear_all_caches()
    >>> # test
    >>> if 'cPREFIX' in os.environ:
    ...    discard = get_pip_prefix()
    >>> # teardown
    >>> clear_all_caches()

    """
    c_parts: List[str] = list()
    c_parts.append(os.getenv("cPREFIX", ""))
    c_parts.append(os.getenv("cPIP", ""))
    command_prefix = " ".join(c_parts).strip()
    return command_prefix


@lru_cache(maxsize=None)
def get_python_prefix() -> str:
    """
    get the python_prefix including the command prefix like : 'wine python'

    >>> # setup
    >>> clear_all_caches()
    >>> # test
    >>> if 'cPREFIX' in os.environ:
    ...    discard = get_python_prefix()
    >>> clear_all_caches()

    """
    c_parts: List[str] = list()
    c_parts.append(os.getenv("cPREFIX", ""))
    c_parts.append(os.getenv("cPYTHON", ""))
    python_prefix = " ".join(c_parts).strip()
    return python_prefix


@lru_cache(maxsize=None)
def get_github_username() -> str:
    """
    get the github username like 'bitranox' (the OWNER of the Repository !)

    >>> # setup
    >>> clear_all_caches()
    >>> # test
    >>> discard = get_github_username()
    >>> clear_all_caches()

    """
    return get_env_data("GITHUB_REPOSITORY_OWNER")


@lru_cache(maxsize=None)
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
    >>> clear_all_caches()

    >>> # BUILD_TEST != 'True'
    >>> os.environ['MYPY_DO_TESTS'] = 'false'
    >>> assert not do_mypy_tests()
    >>> clear_all_caches()

    >>> # BUILD_TEST == 'true'
    >>> os.environ['MYPY_DO_TESTS'] = 'True'
    >>> assert do_mypy_tests()
    >>> clear_all_caches()

    >>> # Teardown
    >>> if save_do_mypy is None:
    ...     os.unsetenv('MYPY_DO_TESTS')
    ... else:
    ...     os.environ['MYPY_DO_TESTS'] = save_do_mypy
    >>> clear_all_caches()
    """

    if os.getenv("MYPY_DO_TESTS", "").lower() == "true":
        return True
    else:
        return False


@lru_cache(maxsize=None)
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
    >>> clear_all_caches()

    >>> # BUILD_TEST != 'True'
    >>> os.environ['PYTEST_DO_TESTS'] = 'false'
    >>> assert not do_pytest()
    >>> clear_all_caches()

    >>> # BUILD_TEST == 'true'
    >>> os.environ['PYTEST_DO_TESTS'] = 'True'
    >>> assert do_pytest()
    >>> clear_all_caches()

    >>> # Teardown
    >>> if save_do_pytest is None:
    ...     os.unsetenv('PYTEST_DO_TESTS')
    ... else:
    ...     os.environ['PYTEST_DO_TESTS'] = save_do_pytest
    >>> clear_all_caches()
    """
    if os.getenv("PYTEST_DO_TESTS", "").lower() == "true":
        return True
    else:
        return False


@lru_cache(maxsize=None)
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
    >>> clear_all_caches()

    >>> # BUILD_TEST != 'True'
    >>> os.environ['DO_COVERAGE'] = 'false'
    >>> assert not do_coverage()
    >>> clear_all_caches()

    >>> # BUILD_TEST == 'true'
    >>> os.environ['DO_COVERAGE'] = 'True'
    >>> assert do_coverage()
    >>> clear_all_caches()

    >>> # Teardown
    >>> if save_do_coverage is None:
    ...     os.unsetenv('DO_COVERAGE')
    ... else:
    ...     os.environ['DO_COVERAGE'] = save_do_coverage
    >>> clear_all_caches()

    """
    return get_env_data("DO_COVERAGE").lower() == "true"


@lru_cache(maxsize=None)
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
    >>> clear_all_caches()

    >>> # BUILD_TEST != 'True'
    >>> os.environ['DO_COVERAGE_UPLOAD_CODECOV'] = 'false'
    >>> assert not do_upload_codecov()
    >>> clear_all_caches()

    >>> # BUILD_TEST == 'true'
    >>> os.environ['DO_COVERAGE_UPLOAD_CODECOV'] = 'True'
    >>> assert do_upload_codecov()
    >>> clear_all_caches()

    >>> # Teardown
    >>> if save_upload_codecov is None:
    ...     os.unsetenv('DO_COVERAGE_UPLOAD_CODECOV')
    ... else:
    ...     os.environ['DO_COVERAGE_UPLOAD_CODECOV'] = save_upload_codecov
    >>> clear_all_caches()

    """
    return get_env_data("DO_COVERAGE_UPLOAD_CODECOV").lower() == "true"


@lru_cache(maxsize=None)
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
    >>> clear_all_caches()

    >>> # BUILD_TEST != 'True'
    >>> os.environ['DO_COVERAGE_UPLOAD_CODE_CLIMATE'] = 'false'
    >>> assert not do_upload_code_climate()
    >>> clear_all_caches()

    >>> # BUILD_TEST == 'true'
    >>> os.environ['DO_COVERAGE_UPLOAD_CODE_CLIMATE'] = 'True'
    >>> assert do_upload_code_climate()
    >>> clear_all_caches()

    >>> # Teardown
    >>> if save_upload_code_climate is None:
    ...     os.unsetenv('DO_COVERAGE_UPLOAD_CODE_CLIMATE')
    ... else:
    ...     os.environ['DO_COVERAGE_UPLOAD_CODE_CLIMATE'] = save_upload_code_climate
    >>> clear_all_caches()
    """
    return get_env_data("DO_COVERAGE_UPLOAD_CODE_CLIMATE").lower() == "true"


@lru_cache(maxsize=None)
def do_setup_py() -> bool:
    return get_env_data("DO_SETUP_INSTALL").lower() == "true"


@lru_cache(maxsize=None)
def do_setup_py_test() -> bool:
    return get_env_data("DO_SETUP_INSTALL_TEST").lower() == "true"


@lru_cache(maxsize=None)
def do_check_cli() -> bool:
    return get_env_data("DO_CLI_TEST").lower() == "true"


@lru_cache(maxsize=None)
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
    >>> save_build_docs = get_env_data('BUILD_DOCS')
    >>> save_rst_include_source = get_env_data('RST_INCLUDE_SOURCE')
    >>> save_rst_include_target = get_env_data('RST_INCLUDE_TARGET')
    >>> clear_all_caches()

    >>> # BUILD_DOCS != 'true'
    >>> set_env_data('BUILD_DOCS', 'false')
    >>> set_env_data('RST_INCLUDE_SOURCE', '')
    >>> set_env_data('RST_INCLUDE_TARGET', '')
    >>> assert do_build_docs() == False
    >>> clear_all_caches()

    >>> # BUILD_DOCS == 'true', no source, no target
    >>> set_env_data('BUILD_DOCS', 'true')
    >>> set_env_data('RST_INCLUDE_SOURCE', '')
    >>> set_env_data('RST_INCLUDE_TARGET', '')
    >>> assert do_build_docs() == False
    >>> clear_all_caches()

    >>> # BUILD_DOCS == 'true', no source
    >>> set_env_data('BUILD_DOCS', 'true')
    >>> set_env_data('RST_INCLUDE_SOURCE', '')
    >>> set_env_data('RST_INCLUDE_TARGET', 'some_target')
    >>> assert do_build_docs() == False
    >>> clear_all_caches()

    >>> # BUILD_DOCS == 'true', source and target
    >>> set_env_data('BUILD_DOCS', 'true')
    >>> set_env_data('RST_INCLUDE_SOURCE', 'some_source')
    >>> set_env_data('RST_INCLUDE_TARGET', 'some_target')
    >>> assert do_build_docs() == True
    >>> clear_all_caches()

    >>> # Teardown
    >>> set_env_data('BUILD_DOCS', save_build_docs)
    >>> set_env_data('RST_INCLUDE_SOURCE', save_rst_include_source)
    >>> set_env_data('RST_INCLUDE_TARGET', save_rst_include_target)
    >>> clear_all_caches()
    """
    if get_env_data("BUILD_DOCS").lower() != "true":
        return False

    if not get_env_data("RST_INCLUDE_SOURCE"):
        return False

    if not get_env_data("RST_INCLUDE_TARGET"):
        return False
    else:
        return True


@lru_cache(maxsize=None)
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
    >>> clear_all_caches()

    >>> # DO_FLAKE8_TESTS != 'true'
    >>> os.environ['DO_FLAKE8_TESTS'] = 'false'
    >>> assert not do_flake8_tests()
    >>> clear_all_caches()

    >>> # DO_FLAKE8_TESTS == 'true'
    >>> os.environ['DO_FLAKE8_TESTS'] = 'True'
    >>> assert do_flake8_tests()
    >>> clear_all_caches()

    >>> # Teardown
    >>> if save_flake8_test is None:
    ...     os.unsetenv('DO_FLAKE8_TESTS')
    ... else:
    ...     os.environ['DO_FLAKE8_TESTS'] = save_flake8_test
    >>> clear_all_caches()
    """
    if os.getenv("DO_FLAKE8_TESTS", "").lower() == "true":
        return True
    else:
        return False


@lru_cache(maxsize=None)
def do_build() -> bool:
    """
    if a build (sdist and wheel) should be done

    Parameter
    ---------
    BUILD
        from environment

    Examples:

    >>> # Setup
    >>> save_build = os.getenv('BUILD')
    >>> clear_all_caches()

    >>> # BUILD_TEST != 'True'
    >>> os.environ['BUILD'] = 'false'
    >>> assert not do_build()
    >>> clear_all_caches()

    >>> # BUILD_TEST == 'true'
    >>> os.environ['BUILD'] = 'True'
    >>> assert do_build()
    >>> clear_all_caches()

    >>> # Teardown
    >>> if save_build is None:
    ...     os.unsetenv('BUILD')
    ... else:
    ...     os.environ['BUILD'] = save_build
    >>> clear_all_caches()
    """
    if os.getenv("BUILD", "").lower() == "true":
        return True
    else:
        return False


@lru_cache(maxsize=None)
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
    >>> clear_all_caches()

    >>> # BUILD_TEST != 'True'
    >>> os.environ['BUILD_TEST'] = 'false'
    >>> assert not do_build_test()
    >>> clear_all_caches()

    >>> # BUILD_TEST == 'true'
    >>> os.environ['BUILD_TEST'] = 'True'
    >>> assert do_build_test()
    >>> clear_all_caches()

    >>> # Teardown
    >>> if save_build_test is None:
    ...     os.unsetenv('BUILD_TEST')
    ... else:
    ...     os.environ['BUILD_TEST'] = save_build_test
    >>> clear_all_caches()
    """
    if os.getenv("BUILD_TEST", "").lower() == "true":
        return True
    else:
        return False


@lru_cache(maxsize=None)
def is_pypy3() -> bool:
    """
    if it is a pypy3 build

    Parameter
    ---------
    matrix.python-version
        from environment

    Examples:

    >>> # Setup
    >>> save_python_version = get_env_data('matrix.python-version')
    >>> clear_all_caches()

    >>> # Test
    >>> set_env_data('matrix.python-version', 'pypy-3.7')
    >>> assert is_pypy3() == True
    >>> clear_all_caches()

    >>> set_env_data('matrix.python-version', '3.9')
    >>> assert is_pypy3() == False
    >>> clear_all_caches()

    >>> # Teardown
    >>> set_env_data('matrix.python-version', save_python_version)
    >>> clear_all_caches()
    """
    return get_env_data("matrix.python-version").lower().startswith("pypy-3")


@lru_cache(maxsize=None)
def is_ci_runner_os_windows() -> bool:
    """
    if the ci runner os is windows

    Parameter
    ---------
    runner.os
        from environment

    Examples:

    >>> # Setup
    >>> save_gha_os_name = get_env_data('RUNNER_OS')
    >>> clear_all_caches()

    >>> # runner.os == 'linux'
    >>> set_env_data('RUNNER_OS', 'Linux')
    >>> assert is_ci_runner_os_windows() == False
    >>> clear_all_caches()

    >>> # TRAVIS_OS_NAME == 'windows'
    >>> set_env_data('RUNNER_OS', 'Windows')
    >>> assert is_ci_runner_os_windows() == True
    >>> clear_all_caches()

    >>> # Teardown
    >>> set_env_data('RUNNER_OS', save_gha_os_name)
    >>> clear_all_caches()
    """
    return get_env_data("RUNNER_OS").lower() == "windows"


@lru_cache(maxsize=None)
def is_ci_runner_os_linux() -> bool:
    """
    if the ci runner os is linux

    Parameter
    ---------
    runner.os
        from environment

    Examples:

    >>> # Setup
    >>> save_gha_os_name = get_env_data('RUNNER_OS')
    >>> clear_all_caches()

    >>> # runner.os == 'linux'
    >>> set_env_data('RUNNER_OS', 'Linux')
    >>> assert is_ci_runner_os_linux() == True
    >>> clear_all_caches()

    >>> # TRAVIS_OS_NAME == 'windows'
    >>> set_env_data('RUNNER_OS', 'Windows')
    >>> assert is_ci_runner_os_linux() == False
    >>> clear_all_caches()

    >>> # Teardown
    >>> set_env_data('RUNNER_OS', save_gha_os_name)
    >>> clear_all_caches()
    """
    return get_env_data("RUNNER_OS").lower() == "linux"


@lru_cache(maxsize=None)
def is_ci_runner_os_macos() -> bool:
    """
    if the ci runner os is macos

    Parameter
    ---------
    RUNNER_OS
        from environment

    Examples:

    >>> # Setup
    >>> save_gha_os_name = get_env_data('RUNNER_OS')
    >>> clear_all_caches()

    >>> # runner.os == 'linux'
    >>> set_env_data('RUNNER_OS', 'Linux')
    >>> assert is_ci_runner_os_macos() == False
    >>> clear_all_caches()

    >>> # TRAVIS_OS_NAME == 'windows'
    >>> set_env_data('RUNNER_OS', 'macOS')
    >>> assert is_ci_runner_os_macos() == True
    >>> clear_all_caches()

    >>> # Teardown
    >>> set_env_data('RUNNER_OS', save_gha_os_name)
    >>> clear_all_caches()
    """
    return get_env_data("RUNNER_OS").lower() == "macos"


@lru_cache(maxsize=None)
def do_deploy() -> bool:
    """
    if we should deploy
    if (DEPLOY_SDIST  or DEPLOY_WHEEL) and is_release()

    Parameter
    ---------
    DEPLOY_SDIST
        from environment
    DEPLOY_WHEEL
        from environment
    GITHUB_EVENT_NAME
        from environment

    Examples:

    >>> # Setup
    >>> save_github_event_name = get_env_data('GITHUB_EVENT_NAME')
    >>> save_build = get_env_data('BUILD')
    >>> clear_all_caches()

    >>> # no Tagged Commit
    >>> set_env_data('GITHUB_EVENT_NAME', 'push')
    >>> assert False == do_deploy()
    >>> clear_all_caches()

    >>> # Tagged Commit, DEPLOY_SDIST, DEPLOY_WHEEL != True
    >>> set_env_data('GITHUB_EVENT_NAME', 'release')
    >>> set_env_data('BUILD', '')
    >>> assert False == do_deploy()
    >>> clear_all_caches()

    >>> # Tagged Commit, DEPLOY_SDIST == True
    >>> set_env_data('GITHUB_EVENT_NAME', 'release')
    >>> set_env_data('BUILD', 'True')
    >>> assert True == do_deploy()
    >>> clear_all_caches()

    >>> # Teardown
    >>> set_env_data('GITHUB_EVENT_NAME', save_github_event_name)
    >>> set_env_data('BUILD', save_build)
    >>> clear_all_caches()
    """
    return do_build() and is_release()


@lru_cache(maxsize=None)
def is_release() -> bool:
    """
    Returns True, if this is a release (and then we deploy to pypi probably)
    """
    return get_env_data("GITHUB_EVENT_NAME") == "release"


@lru_cache(maxsize=None)
def get_env_data(env_variable: str) -> str:
    """
    >>> # Setup
    >>> save_mypy_path = get_env_data('MYPYPATH')
    >>> clear_all_caches()

    >>> # Test
    >>> set_env_data('MYPYPATH', 'some_test')
    >>> assert get_env_data('MYPYPATH') == 'some_test'
    >>> clear_all_caches()

    >>> # Teardown
    >>> set_env_data('MYPYPATH', save_mypy_path)
    >>> clear_all_caches()
    """
    if env_variable in os.environ:
        env_data = os.environ[env_variable]
    else:
        env_data = ""
    return env_data


def set_env_data(env_variable: str, env_str: str) -> None:
    os.environ[env_variable] = env_str


@lru_cache(maxsize=None)
def is_github_actions_active() -> bool:
    """
    if we are on github actions environment

    >>> # Setup
    >>> clear_all_caches()

    >>> # Test
    >>> assert is_github_actions_active() == is_github_actions_active()

    >>> # Teardown
    >>> clear_all_caches()
    """
    return bool(get_env_data("CI") and get_env_data("GITHUB_WORKFLOW") and get_env_data("GITHUB_RUN_ID"))


def clear_all_caches():
    is_github_actions_active.cache_clear()
    get_env_data.cache_clear()
    is_release.cache_clear()
    do_deploy.cache_clear()
    do_build.cache_clear()
    do_build_docs.cache_clear()
    do_build_test.cache_clear()
    is_ci_runner_os_macos.cache_clear()
    is_ci_runner_os_linux.cache_clear()
    is_ci_runner_os_windows.cache_clear()
    is_pypy3.cache_clear()
    do_flake8_tests.cache_clear()
    do_check_cli.cache_clear()
    do_setup_py_test.cache_clear()
    do_setup_py.cache_clear()
    do_upload_code_climate.cache_clear()
    do_upload_codecov.cache_clear()
    do_coverage.cache_clear()
    do_pytest.cache_clear()
    do_mypy_tests.cache_clear()
    get_github_username.cache_clear()
    get_python_prefix.cache_clear()
    get_pip_prefix.cache_clear()
    get_branch.cache_clear()


if __name__ == "__main__":
    print(
        b'this is a library only, the executable is named "lib_cicd_github_cli.py"',
        file=sys.stderr,
    )
