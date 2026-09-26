import logging
from pathlib import Path


def setup_logging():

    # Riot_Data_Pipeline/
    project_root = Path(__file__).resolve().parents[2]

    # Riot_Data_Pipeline/logs/
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)

    # Riot_Data_Pipeline/logs/pipeline.log
    log_file = log_dir / "pipeline.log"

    # Format shared by all handlers
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    # File handler: record detailed information
    file_handler = logging.FileHandler(
        log_file,
        mode="a",
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler: show important runtime information
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)