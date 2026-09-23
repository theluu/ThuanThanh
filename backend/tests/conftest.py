import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.db import read_csv  # noqa: E402


@pytest.fixture(scope="session")
def train_df():
    return read_csv(config.TRAIN_CSV)


@pytest.fixture(scope="session")
def eval_df():
    return read_csv(config.EVAL_CSV)
