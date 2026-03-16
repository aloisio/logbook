import pytest
from typing import Any


@pytest.fixture
def case(request) -> Any:
    return request.getfixturevalue(request.param)
