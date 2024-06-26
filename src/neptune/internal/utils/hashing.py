#
# Copyright (c) 2023, Neptune Labs Sp. z o.o.
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
__all__ = ["generate_hash"]

import hashlib
from typing import Any


def generate_hash(*descriptors: Any, length: int) -> str:
    hasher = hashlib.sha256()

    for descriptor in descriptors:
        hasher.update(str(descriptor).encode())

    return hasher.hexdigest()[-length:]
