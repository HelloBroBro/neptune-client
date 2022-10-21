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
from neptune._version import get_versions
from neptune.legacy import (
    ANONYMOUS,
    ANONYMOUS_API_TOKEN,
    InvalidNeptuneBackend,
    NeptuneIncorrectImportException,
    NeptuneUninitializedException,
    Project,
    Session,
    append_tag,
    append_tags,
    assure_project_qualified_name,
    backend_factory,
    create_experiment,
    delete_artifacts,
    get_experiment,
    init,
    log_artifact,
    log_image,
    log_metric,
    log_text,
    project,
    remove_property,
    remove_tag,
    send_artifact,
    send_image,
    send_metric,
    send_text,
    session,
    set_project,
    set_property,
    stop,
)

__version__ = get_versions()["version"]