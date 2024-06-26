#
# Copyright (c) 2021, Neptune Labs Sp. z o.o.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
__all__ = [
    "tmp_context",
    "a_key",
    "Environment",
    "initialize_container",
    "reinitialize_container",
    "modified_environ",
    "catch_time",
]

import os
import random
import string
import tempfile
from contextlib import contextmanager
from time import perf_counter

from attr import dataclass

import neptune
from neptune.internal.container_type import ContainerType
from tests.e2e.exceptions import MissingEnvironmentVariable

# init kwargs which significantly reduce operations noise
DISABLE_SYSLOG_KWARGS = {
    "capture_stdout": False,
    "capture_stderr": False,
    "capture_hardware_metrics": False,
}


@contextmanager
def preserve_cwd(path):
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


@contextmanager
def tmp_context():
    with tempfile.TemporaryDirectory() as tmp:
        with preserve_cwd(tmp):
            yield tmp


def a_key():
    return "".join(random.choices(string.ascii_uppercase, k=10))


class RawEnvironment:
    """Load environment variables required to run e2e tests"""

    def __init__(self):
        env = os.environ
        try:
            # Target workspace name
            self.project_name = env["NEPTUNE_PROJECT"]
            # Member user or SA API token
            self.neptune_api_token = env["NEPTUNE_API_TOKEN"]
        except KeyError as e:
            raise MissingEnvironmentVariable(missing_variable=e.args[0]) from e


@dataclass
class Environment:
    project: str
    user_token: str


def initialize_container(container_type, project, **extra_args):
    if isinstance(container_type, ContainerType):
        container_type = container_type.value

    if container_type == "project":
        return neptune.init_project(project=project, **extra_args)

    if container_type == "run":
        return neptune.init_run(project=project, **extra_args)

    raise NotImplementedError(container_type)


def reinitialize_container(sys_id: str, container_type: str, project: str, **kwargs):
    if container_type == "project":
        # exactly same as initialize_container(project), for convenience
        return neptune.init_project(project=project, **kwargs)

    if container_type == "run":
        return neptune.init_run(with_id=sys_id, project=project, **kwargs)

    raise NotImplementedError()


# from https://stackoverflow.com/a/62956469
@contextmanager
def catch_time() -> float:
    start = perf_counter()
    yield lambda: perf_counter() - start


# from https://stackoverflow.com/a/34333710
@contextmanager
def modified_environ(*remove, **update):
    """
    Temporarily updates the ``os.environ`` dictionary in-place.

    The ``os.environ`` dictionary is updated in-place so that the modification
    is sure to work in all situations.

    :param remove: Environment variables to remove.
    :param update: Dictionary of environment variables and values to add/update.
    """
    env = os.environ
    update = update or {}
    remove = remove or []

    # List of environment variables being updated or removed.
    stomped = (set(update.keys()) | set(remove)) & set(env.keys())
    # Environment variables and values to restore on exit.
    update_after = {k: env[k] for k in stomped}
    # Environment variables and values to remove on exit.
    remove_after = frozenset(k for k in update if k not in env)

    try:
        env.update(update)
        for k in remove:
            env.pop(k, None)
        yield
    finally:
        env.update(update_after)
        for k in remove_after:
            env.pop(k)
