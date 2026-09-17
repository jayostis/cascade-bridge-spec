"""The validators a check reads the shapes and the reports with, installed once the version is picked."""

import os
import shutil
import subprocess
import sys

from compatibility_tool.bootstrap import SPEC_ROOT
from compatibility_tool.console import Stop

VALIDATOR = "rocrate-validator"
BY_HAND = "python3 -m pip install --group <cascade-bridge-spec>/pyproject.toml:validators"


def install():
    if os.environ.get("CI") != "true":
        return
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--group", f"{SPEC_ROOT / 'pyproject.toml'}:validators"],
        check=False,
    )


def installed(name):
    try:
        return __import__(name)
    except ImportError:
        install()
    try:
        return __import__(name)
    except ImportError as error:
        raise Stop(f"{name} is not installed, and the checks read the shapes with it: {BY_HAND}") from error


def validator():
    found = shutil.which(VALIDATOR)
    if found is None:
        install()
        found = shutil.which(VALIDATOR)
    if found is None:
        raise Stop(f"{VALIDATOR} is not installed, and it is what lints an adapter's crate: {BY_HAND}")
    return found
