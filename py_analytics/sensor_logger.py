import logging
import os
import re
from logging.handlers import RotatingFileHandler


class SensorLogger:
    """File-only point and anomaly logs for one sensor."""

    def __init__(self, source_name: str, strategy_name: str | None = None, log_dir: str = "logs"):
        safe_source = self._safe_name(source_name)
        telemetry_dir = os.path.join(log_dir, "telemetry")
        anomaly_dir = os.path.join(log_dir, "analysis", "warnings")
        os.makedirs(telemetry_dir, exist_ok=True)

        self.data_logger = self._file_logger(
            f"py_analytics.sensor_data.{safe_source}",
            os.path.join(telemetry_dir, f"{safe_source}_data.log"),
        )
        self.anomaly_logger = None
        if strategy_name:
            os.makedirs(anomaly_dir, exist_ok=True)
            safe_strategy = self._safe_name(strategy_name)
            self.anomaly_logger = self._file_logger(
                f"py_analytics.sensor_anomalies.{safe_source}.{safe_strategy}",
                os.path.join(anomaly_dir, f"{safe_source}_{safe_strategy}_anomalies.log"),
            )

    @staticmethod
    def _safe_name(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("._") or "sensor"

    @staticmethod
    def _file_logger(name: str, path: str) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        if not logger.handlers:
            handler = RotatingFileHandler(
                path,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
            logger.addHandler(handler)
        return logger

    def log_datapoint(self, batch_id, timestamp, value) -> None:
        self.data_logger.info(
            "batch_id=%s timestamp=%s value=%s", batch_id, timestamp, value
        )

    def log_anomaly(self, batch_id, timestamp, value, score=None) -> None:
        if self.anomaly_logger is None:
            return
        self.anomaly_logger.warning(
            "batch_id=%s timestamp=%s value=%s anomaly_score=%s",
            batch_id,
            timestamp,
            value,
            score if score is not None else "n/a",
        )
