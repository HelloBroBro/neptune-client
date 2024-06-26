#
# Copyright (c) 2022, Neptune Labs Sp. z o.o.
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
import itertools
import os
import unittest

import pytest
from mock import (
    mock_open,
    patch,
)

from neptune import (
    ANONYMOUS_API_TOKEN,
    init_run,
)
from neptune.api.models import (
    FieldDefinition,
    FieldType,
    IntField,
)
from neptune.attributes.atoms import String
from neptune.envs import (
    API_TOKEN_ENV_NAME,
    PROJECT_ENV_NAME,
)
from neptune.exceptions import (
    MissingFieldException,
    NeptuneException,
)
from neptune.internal.backends.neptune_backend_mock import NeptuneBackendMock
from neptune.internal.utils.limits import CUSTOM_RUN_ID_LENGTH
from neptune.internal.utils.paths import path_to_str
from neptune.internal.utils.utils import IS_WINDOWS
from neptune.internal.warnings import (
    NeptuneWarning,
    warned_once,
)
from neptune.objects import NeptuneObject
from tests.unit.neptune.new.client.abstract_experiment_test_mixin import AbstractExperimentTestMixin
from tests.unit.neptune.new.utils.api_experiments_factory import api_run

AN_API_RUN = api_run()


@patch("neptune.internal.backends.factory.HostedNeptuneBackend", NeptuneBackendMock)
class TestClientRun(AbstractExperimentTestMixin, unittest.TestCase):
    @staticmethod
    @patch.object(
        NeptuneObject,
        "_async_create_run",
        lambda self: self._backend._create_container(self._custom_id, self.container_type, self._project_id),
    )
    def call_init(**kwargs):
        return init_run(**kwargs)

    @classmethod
    def setUpClass(cls) -> None:
        os.environ[PROJECT_ENV_NAME] = "organization/project"
        os.environ[API_TOKEN_ENV_NAME] = ANONYMOUS_API_TOKEN

    @patch(
        "neptune.internal.backends.neptune_backend_mock.NeptuneBackendMock.get_metadata_container",
        new=lambda _, container_id, expected_container_type: AN_API_RUN,
    )
    @patch(
        "neptune.internal.backends.neptune_backend_mock.NeptuneBackendMock.get_attributes",
        new=lambda _, _uuid, _type: [FieldDefinition("some/variable", FieldType.INT)],
    )
    @patch(
        "neptune.internal.backends.neptune_backend_mock.NeptuneBackendMock.get_int_attribute",
        new=lambda _, _uuid, _type, _path: IntField(value=42, path=path_to_str(_path)),
    )
    @patch("neptune.core.operation_processors.read_only_operation_processor.warn_once")
    def test_read_only_mode(self, warn_once):
        warned_once.clear()
        with init_run(mode="read-only", with_id="whatever") as exp:
            exp["some/variable"] = 13
            exp["some/other_variable"] = 11

            warn_once.assert_called_with(
                "Client in read-only mode, nothing will be saved to server.", exception=NeptuneWarning
            )
            self.assertEqual(42, exp["some/variable"].fetch())
            self.assertNotIn(str(exp._custom_id), os.listdir(".neptune"))

    @unittest.skip("Test disabled due to changes in the API")
    @patch(
        "neptune.internal.backends.neptune_backend_mock.NeptuneBackendMock.get_metadata_container",
        new=lambda _, container_id, expected_container_type: AN_API_RUN,
    )
    @patch(
        "neptune.internal.backends.neptune_backend_mock.NeptuneBackendMock.get_attributes",
        new=lambda _, _uuid, _type: [FieldDefinition("test", FieldType.STRING)],
    )
    def test_resume(self):
        with init_run(flush_period=0.5, with_id="whatever") as exp:
            self.assertEqual(exp._custom_id, AN_API_RUN.id)
            self.assertIsInstance(exp.get_structure()["test"], String)

    @pytest.mark.skip("Temporarily disabled - will be brought back in 2.0.0")
    @patch("neptune.internal.utils.source_code.get_path_executed_script", lambda: "main.py")
    @patch("neptune.objects.run.os.path.isfile", new=lambda file: "." in file)
    @patch(
        "neptune.internal.utils.glob",
        new=lambda path, recursive=False: [path.replace("*", "file.txt")],
    )
    @patch(
        "neptune.internal.utils.os.path.abspath",
        new=lambda path: os.path.normpath(os.path.join("/home/user/main_dir", path)),
    )
    @unittest.skipIf(IS_WINDOWS, "Linux/Mac test")
    @patch("neptune.core.components.operation_storage.os.listdir", new=lambda path: [])
    @patch("neptune.core.components.metadata_file.open", mock_open())
    def test_entrypoint(self):
        with init_run(mode="debug") as exp:
            self.assertEqual(exp["source_code/entrypoint"].fetch(), "main.py")

        with init_run(mode="debug", source_files=[]) as exp:
            self.assertEqual(exp["source_code/entrypoint"].fetch(), "main.py")

        with init_run(mode="debug", source_files=["../*"]) as exp:
            self.assertEqual(exp["source_code/entrypoint"].fetch(), "main_dir/main.py")

        with init_run(mode="debug", source_files=["internal/*"]) as exp:
            self.assertEqual(exp["source_code/entrypoint"].fetch(), "../main.py")

        with init_run(mode="debug", source_files=["../other_dir/*"]) as exp:
            self.assertEqual(exp["source_code/entrypoint"].fetch(), "../main_dir/main.py")

    @pytest.mark.skip(reason="File functionality disabled")
    @patch("neptune.internal.utils.source_code.is_ipython", new=lambda: True)
    def test_entrypoint_in_interactive_python(self):
        with init_run(mode="debug") as exp:
            with self.assertRaises(MissingFieldException):
                exp["source_code/entrypoint"].fetch()

        with init_run(mode="debug", source_files=[]) as exp:
            with self.assertRaises(MissingFieldException):
                exp["source_code/entrypoint"].fetch()

        with init_run(mode="debug", source_files=["../*"]) as exp:
            with self.assertRaises(MissingFieldException):
                exp["source_code/entrypoint"].fetch()

        with init_run(mode="debug", source_files=["internal/*"]) as exp:
            with self.assertRaises(MissingFieldException):
                exp["source_code/entrypoint"].fetch()

    @pytest.mark.skip("Temporarily disabled - will be brought back in 2.0.0")
    @patch("neptune.objects.run.in_interactive", new=lambda: True)
    @patch("neptune.objects.run.TracebackJob")
    @patch("neptune.objects.run.HardwareMetricReportingJob")
    @patch("neptune.objects.run.StderrCaptureBackgroundJob")
    @patch("neptune.objects.run.StdoutCaptureBackgroundJob")
    def test_monitoring_disabled_in_interactive_python(self, stdout_job, stderr_job, hardware_job, traceback_job):
        with init_run(mode="debug", monitoring_namespace="monitoring"):
            assert not stdout_job.called
            assert not stderr_job.called
            assert not hardware_job.called
            traceback_job.assert_called_once_with(path="monitoring/traceback", fail_on_exception=True)

    @pytest.mark.skip("Temporarily disabled - will be brought back in 2.0.0")
    @patch("neptune.objects.run.in_interactive", new=lambda: False)
    @patch("neptune.objects.run.TracebackJob")
    @patch("neptune.objects.run.HardwareMetricReportingJob")
    @patch("neptune.objects.run.StderrCaptureBackgroundJob")
    @patch("neptune.objects.run.StdoutCaptureBackgroundJob")
    def test_monitoring_enabled_in_non_interactive_python(self, stdout_job, stderr_job, hardware_job, traceback_job):
        with init_run(mode="debug", monitoring_namespace="monitoring"):
            stdout_job.assert_called_once_with(attribute_name="monitoring/stdout")
            stderr_job.assert_called_once_with(attribute_name="monitoring/stderr")
            hardware_job.assert_called_once_with(attribute_namespace="monitoring")
            traceback_job.assert_called_once_with(path="monitoring/traceback", fail_on_exception=True)

    @pytest.mark.skip("Temporarily disabled - will be brought back in 2.0.0")
    @patch("neptune.objects.run.in_interactive", new=lambda: True)
    @patch("neptune.objects.run.TracebackJob")
    @patch("neptune.objects.run.HardwareMetricReportingJob")
    @patch("neptune.objects.run.StderrCaptureBackgroundJob")
    @patch("neptune.objects.run.StdoutCaptureBackgroundJob")
    def test_monitoring_in_interactive_explicitly_enabled(self, stdout_job, stderr_job, hardware_job, traceback_job):
        with init_run(
            mode="debug",
            monitoring_namespace="monitoring",
            capture_stdout=True,
            capture_stderr=True,
            capture_hardware_metrics=True,
        ):
            stdout_job.assert_called_once_with(attribute_name="monitoring/stdout")
            stderr_job.assert_called_once_with(attribute_name="monitoring/stderr")
            hardware_job.assert_called_once_with(attribute_namespace="monitoring")
            traceback_job.assert_called_once_with(path="monitoring/traceback", fail_on_exception=True)

    @pytest.mark.skip("Temporarily disabled - will be brought back in 2.0.0")
    @patch("neptune.internal.utils.source_code.get_path_executed_script", lambda: "main.py")
    @patch("neptune.internal.utils.source_code.get_common_root", new=lambda _: None)
    @patch("neptune.objects.run.os.path.isfile", new=lambda file: "." in file)
    @patch(
        "neptune.internal.utils.glob",
        new=lambda path, recursive=False: [path.replace("*", "file.txt")],
    )
    @patch(
        "neptune.internal.utils.os.path.abspath",
        new=lambda path: os.path.normpath(os.path.join("/home/user/main_dir", path)),
    )
    @patch("neptune.core.components.operation_storage.os.listdir", new=lambda path: [])
    @patch("neptune.core.components.metadata_file.open", mock_open())
    def test_entrypoint_without_common_root(self):
        with init_run(mode="debug", source_files=["../*"]) as exp:
            self.assertEqual(exp["source_code/entrypoint"].fetch(), "/home/user/main_dir/main.py")

        with init_run(mode="debug", source_files=["internal/*"]) as exp:
            self.assertEqual(exp["source_code/entrypoint"].fetch(), "/home/user/main_dir/main.py")

    @pytest.mark.skip("Temporarily disabled - will be brought back in 2.0.0")
    @patch("neptune.objects.run.generate_hash", lambda *vals, length: "some_hash")
    @patch("neptune.objects.run.TracebackJob")
    @patch("neptune.objects.run.HardwareMetricReportingJob")
    @patch("neptune.objects.run.StderrCaptureBackgroundJob")
    @patch("neptune.objects.run.StdoutCaptureBackgroundJob")
    def test_monitoring_namespace_based_on_hash(self, stdout_job, stderr_job, hardware_job, traceback_job):
        with init_run(mode="debug"):
            stdout_job.assert_called_once_with(attribute_name="monitoring/some_hash/stdout")
            stderr_job.assert_called_once_with(attribute_name="monitoring/some_hash/stderr")
            hardware_job.assert_called_once_with(attribute_namespace="monitoring/some_hash")
            traceback_job.assert_called_once_with(path="monitoring/some_hash/traceback", fail_on_exception=True)

    @pytest.mark.skip("Temporarily disabled - will be brought back in 2.0.0")
    @patch("neptune.objects.run.generate_hash", lambda *vals, length: "some_hash")
    @patch("neptune.objects.run.get_hostname", lambda *vals: "localhost")
    @patch("neptune.objects.run.os.getpid", lambda *vals: 1234)
    @patch("neptune.objects.run.threading.get_ident", lambda: 56789)
    def test_that_hostname_and_process_info_were_logged(self):
        with init_run(mode="debug") as exp:
            assert exp["monitoring/some_hash/hostname"].fetch() == "localhost"
            assert exp["monitoring/some_hash/pid"].fetch() == "1234"
            assert exp["monitoring/some_hash/tid"].fetch() == "56789"

    @pytest.mark.skip("Temporarily disabled - will be brought back in 2.0.0")
    @patch("neptune.internal.utils.dependency_tracking.InferDependenciesStrategy.log_dependencies")
    def test_infer_dependency_strategy_called(self, mock_infer_method):
        with init_run(mode="debug", dependencies="infer"):
            mock_infer_method.assert_called_once()

    @pytest.mark.skip("Temporarily disabled - will be brought back in 2.0.0")
    @patch("neptune.internal.utils.dependency_tracking.FileDependenciesStrategy.log_dependencies")
    def test_file_dependency_strategy_called(self, mock_file_method):
        with init_run(mode="debug", dependencies="some_file_path.txt"):
            mock_file_method.assert_called_once()

    def test_monitoring_namespace_not_created_if_no_monitoring_enabled(self):
        with init_run(
            mode="debug",
            capture_traceback=False,
            capture_stdout=False,
            capture_stderr=False,
            capture_hardware_metrics=False,
        ) as run:
            assert not run.exists("monitoring")

    @pytest.mark.skip("Temporarily disabled - will be brought back in 2.0.0")
    def test_monitoring_namespace_created_if_any_flag_enabled(self):
        for perm in set(itertools.permutations([True, False, False, False])):
            ct, cso, cse, chm = perm
            with init_run(
                mode="debug",
                capture_traceback=ct,
                capture_stdout=cso,
                capture_stderr=cse,
                capture_hardware_metrics=chm,
            ) as run:
                assert run.exists("monitoring")

    def test_custom_run_id_handling(self):
        lengths = [CUSTOM_RUN_ID_LENGTH, CUSTOM_RUN_ID_LENGTH + 1]
        valid = [True, False]

        for is_valid, length in zip(valid, lengths):
            with self.subTest(is_valid=is_valid, length=length):
                custom_run_id = "a" * length
                if is_valid:
                    init_run(mode="debug", custom_run_id=custom_run_id)
                else:
                    with self.assertRaises(NeptuneException):
                        init_run(mode="debug", custom_run_id=custom_run_id)

    def test_custom_run_id_generation(self):
        with init_run(mode="debug") as run:
            assert isinstance(run._custom_run_id, str)
