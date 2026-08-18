import signal

from ..models.factory import create_strategy
from .worker import ZMQWorker
from ..config.worker_context import WorkerContext

def run_model_worker_process(
        group_config: WorkerContext,
        port: int, # A port on which the ZMQWroker is going to wait for data points from the Cpp side.
        received_strategy: str | None = "SKlearnIsolatedForest",
        serialization: str = "json"):

    """Entry point for the multiprocessing.Process"""

    signal.signal(signal.SIGINT, signal.SIG_IGN)

    folder = "./py_analytics/models"
    strategy = create_strategy(received_strategy, folder)

    worker = ZMQWorker(group_config, port, strategy, serialization)
    worker.start()