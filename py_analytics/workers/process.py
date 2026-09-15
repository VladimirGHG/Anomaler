import signal

from .worker import ZMQWorker
from ..config.worker_context import WorkerContext

def run_model_worker_process(worker_config: WorkerContext, group_runtime_port: int, load_path: str = "", save_every: int = 15, max_snapshots: int = 10, log=True):
    """Entry point for the multiprocessing.Process"""

    signal.signal(signal.SIGINT, signal.SIG_IGN)

    worker = ZMQWorker(worker_config, group_runtime_port, load_path, save_every, max_snapshots, log)
    worker.start()