"""Dependencies injected into agents (data access + tracing) so the graph is testable without Postgres."""
from dataclasses import dataclass
from typing import Callable

import pandas as pd


@dataclass
class Deps:
    load_training: Callable[[], pd.DataFrame]
    load_external: Callable[[], pd.DataFrame]
    trace: Callable[[str, str, str, dict], None]  # (run_id, agent, action, detail)
    external_target: str = "postgresql://lng_external / table lng_prices_eval"
