import signal

from .worker import ZMQWorker
from ..config.worker_context import WorkerContext

def run_model_worker_process(worker_config: WorkerContext):
    """Entry point for the multiprocessing.Process"""

    signal.signal(signal.SIGINT, signal.SIG_IGN)

    worker = ZMQWorker(worker_config)
    worker.start()