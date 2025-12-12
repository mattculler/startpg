import yaml
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = (Path(__file__) / "../../../startpg.yaml").resolve()

def load_config(config_file: Path = DEFAULT_CONFIG) -> Any:
    with config_file.open() as f:
        conf = yaml.safe_load(f)
    breakpoint()
