# STDLIB
import logging
import pathlib
import subprocess
import sys

logger = logging.getLogger()
package_dir = "lib_cicd_github"
cli_filename = "lib_cicd_github_cli.py"

path_cli_command = pathlib.Path(__file__).resolve().parent.parent / package_dir / cli_filename


def call_cli_command(commandline_args: str = "") -> bool:
    command = " ".join([sys.executable, str(path_cli_command), commandline_args])
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError:
        return False
    return True


def test_cli_commands() -> None:
    assert not call_cli_command("--unknown_option")
    assert call_cli_command("--version")
    assert call_cli_command("-h")
    assert call_cli_command("info")
    assert call_cli_command("--traceback info")
    assert call_cli_command("get_branch")

    assert call_cli_command('run test "echo test"')
    assert not call_cli_command('run description "unknown command" --retry=3 --sleep=0')

    assert call_cli_command("install --dry-run")
    assert call_cli_command("script --dry-run")
    assert call_cli_command("after_success --dry-run")
    assert call_cli_command("deploy --dry-run")
