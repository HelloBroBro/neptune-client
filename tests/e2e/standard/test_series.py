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
import random
import time
from contextlib import contextmanager

import pytest

from neptune.exceptions import NeptuneUnsupportedFunctionalityException
from neptune.objects import NeptuneObject
from neptune.types import (
    FloatSeries,
    StringSeries,
)
from tests.e2e.base import (
    AVAILABLE_CONTAINERS,
    BaseE2ETest,
    fake,
    make_parameters,
)

BASIC_SERIES_TYPES = make_parameters(["strings", "floats"]).eval()


@pytest.mark.xfail(
    reason="fetch_last and download_last disabled", strict=True, raises=NeptuneUnsupportedFunctionalityException
)
class TestSeries(BaseE2ETest):
    @pytest.mark.parametrize("series_type", BASIC_SERIES_TYPES)
    @pytest.mark.parametrize("container", AVAILABLE_CONTAINERS, indirect=True)
    def test_log(self, container: NeptuneObject, series_type: str):
        with self.run_then_assert(container, series_type) as (
            namespace,
            values,
            steps,
            timestamps,
        ):
            for value, step, timestamp in zip(values, steps, timestamps):
                namespace.log(value, step=step, timestamp=timestamp)

    @pytest.mark.parametrize("series_type", BASIC_SERIES_TYPES)
    @pytest.mark.parametrize("container", AVAILABLE_CONTAINERS, indirect=True)
    def test_append(self, container: NeptuneObject, series_type: str):
        with self.run_then_assert(container, series_type) as (namespace, values, steps, timestamps):
            for value, step, timestamp in zip(values, steps, timestamps):
                namespace.append(value, step=step, timestamp=timestamp)

    @pytest.mark.parametrize("series_type", BASIC_SERIES_TYPES)
    @pytest.mark.parametrize("container", AVAILABLE_CONTAINERS, indirect=True)
    def test_extend(self, container: NeptuneObject, series_type: str):
        with self.run_then_assert(container, series_type) as (namespace, values, steps, timestamps):
            namespace.extend([values[0]], steps=[steps[0]], timestamps=[timestamps[0]])
            namespace.extend(values[1:], steps=steps[1:], timestamps=timestamps[1:])

    @pytest.mark.parametrize("container", AVAILABLE_CONTAINERS, indirect=True)
    def test_float_series_type_assign(self, container: NeptuneObject):
        with self.run_then_assert(container, "floats") as (namespace, values, steps, timestamps):
            namespace.assign(FloatSeries(values=values, steps=steps, timestamps=timestamps))

    @pytest.mark.parametrize("container", AVAILABLE_CONTAINERS, indirect=True)
    def test_string_series_type_assign(self, container: NeptuneObject):
        with self.run_then_assert(container, "strings") as (namespace, values, steps, timestamps):
            namespace.assign(StringSeries(values=values, steps=steps, timestamps=timestamps))

    @contextmanager
    def run_then_assert(self, container: NeptuneObject, series_type: str):
        steps = sorted(random.sample(range(1, 100), 5))
        timestamps = [
            1675876469.0,
            1675876470.0,
            1675876471.0,
            1675876472.0,
            1675876473.0,
        ]
        key = self.gen_key()

        if series_type == "floats":
            # given
            values = list(random.random() for _ in range(5))

            # when
            yield container[key], values, steps, timestamps
            container.sync()

            # then
            assert container[key].fetch_last() == values[-1]
            assert list(container[key].fetch_values()["value"]) == values
            assert list(container[key].fetch_values()["step"]) == steps
            assert (
                list(map(lambda t: time.mktime(t.utctimetuple()), container[key].fetch_values()["timestamp"]))
                == timestamps
            )

        elif series_type == "strings":
            # given
            values = list(fake.word() for _ in range(5))

            # when
            yield container[key], values, steps, timestamps

            container.sync()

            # then
            assert container[key].fetch_last() == values[-1]
            assert list(container[key].fetch_values()["value"]) == values
            assert list(container[key].fetch_values()["step"]) == steps
            assert (
                list(map(lambda t: time.mktime(t.utctimetuple()), container[key].fetch_values()["timestamp"]))
                == timestamps
            )
