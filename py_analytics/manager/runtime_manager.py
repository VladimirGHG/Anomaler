import multiprocessing
import sys

import zmq

from ..config.group_config import GroupConfig
from ..config.stream_config import StreamConfig
from .group_runtime import GroupRuntime

from ..config.worker_context import WorkerContext
from ..workers.process import run_model_worker_process
from ..transport.FlatBuffers.FlatBuffersReceiver import FlatBuffersReceiver

class RuntimeManager:
    def __init__(self, discovery_socket):

        self.discovery_socket = discovery_socket
        self.groups: dict[str, GroupRuntime] = {}
        self.group_sockets: dict[str, zmq.Socket] = {}
        self.socket_to_group: dict[zmq.Socket, GroupRuntime] = {}
        self.socket_to_receiver: dict[zmq.Socket, FlatBuffersReceiver] = {}

        self.active_workers = []
        self._contexts: dict[str, WorkerContext] = {}

        self.zmqcontext = zmq.Context()
        self.poller = zmq.Poller()

        self.poller.register(self.discovery_socket, zmq.POLLIN)

        self.running = True

    def run(self):
        while self.running:
            events = dict(self.poller.poll())
            print(f"[MANAGER] Poller events: {events}")

            for socket, event in events.items():
                print(
                    f"[MANAGER] Event: socket={socket}, "
                    f"event={event}, "
                    f"is_discovery={socket is self.discovery_socket}, "
                    f"is_group={socket in self.socket_to_group}"
                )

                if not (event & zmq.POLLIN):
                    continue

                if socket is self.discovery_socket:
                    try:
                        msg = socket.recv_json(zmq.DONTWAIT)
                        print(f"[MANAGER] Received message: {msg}")
                    except zmq.Again:
                        print("[MANAGER] Socket became unreadable")
                        continue

                    self.register(msg)
                    continue

                # if socket in self.socket_to_group:
                #     group = self.socket_to_group.get(socket)

                #     if group is None:
                #         continue

                if socket in self.socket_to_receiver:
                    group = self.socket_to_group[socket]
                    receiver = self.socket_to_receiver.get(socket)

                    # print(
                    #     f"[MANAGER] GROUP SOCKET READABLE: "
                    #     f"group={group.group_id}"
                    # )

                    batch = receiver.receive()

                    # print(
                    #     f"[MANAGER] Received batch from "
                    #     f"group '{group.group_id}': {batch}"
                    # )
                    
                    if batch is not None:
                        group.handle_worker_batch(batch)

    def register(self, msg):
        self.poller.register(self.discovery_socket, zmq.POLLIN)

        action = msg.get('action')
        # print(f"--- [MANAGER] Received action '{action}' with message: {msg}")
        if action == "register_stream":
            self._register_stream(msg)
        elif action == "register_group":
            self._register_group(msg)
        else:
            raise NameError(f"No '{action}' action found!")

    def _register_group(self, msg):
        try:
            if not isinstance(msg, dict):
                raise TypeError("Invalid message format")

            group_id = msg.get("group_id")
            config = GroupConfig.from_dict(msg)
            
            if group_id in self.groups:
                raise ValueError(f"Group '{group_id}' is already registered")

            group = GroupRuntime(group_id=group_id, config=config)

            group_socket = self.zmqcontext.socket(zmq.PULL)
            group_socket.bind(f"tcp://{config.communication_host}:{config.communication_port}")

            # print(
            #     f"[MANAGER] PULL binding to "
            #     f"tcp://{config.communication_host}:{config.communication_port}"
            # )

            self.groups[group_id] = group
            self.poller.register(group_socket, zmq.POLLIN)

            # print(
            #     f"[MANAGER] Registered group socket: {group_socket}, "
            #     f"FD={group_socket.getsockopt(zmq.FD)}"
            # )

            # print(
            #     f"[MANAGER] Poller registrations: "
            #     f"{self.poller._map}"
            # )

            self.socket_to_group[group_socket] = group
            self.group_sockets[group_id] = group_socket

            receiver = FlatBuffersReceiver(group_socket)
            self.socket_to_receiver[group_socket] = receiver

            self.discovery_socket.send_json({
                "status": "group_registered",
                "id": group_id,
                "port": config.communication_port,
            })

            print(f"--- [MANAGER] Registered group {group_id}")

        except (ValueError, TypeError) as validation_err:
            print(f"--- [ERROR] Validation error: {validation_err}")
            self.discovery_socket.send_json({"status": "error", "message": f"Validation failed: {validation_err}"})

    def _register_stream(self, msg):
        try:
            stream_port = None
            strategy = None
            if isinstance(msg, dict):
                group_id = msg.get('group_id', None)
                _stream_config = StreamConfig.from_dict(msg)

                self.groups[group_id].register_worker(_stream_config)
                stream_port = _stream_config.port
                strategy = _stream_config.strategy
                self._contexts[f"{group_id}.{_stream_config.source_name}"] = WorkerContext(group_id=group_id,
                                                                                group_runtime=self.groups[group_id],
                                                                                stream_config=_stream_config)

            if not stream_port or not isinstance(stream_port, int) or not (1024 <= stream_port <= 65535):
                raise ValueError(f"Invalid or out-of-bounds network port specified: {stream_port}")
            
            if not isinstance(strategy, (str, type(None))) or (isinstance(strategy, str) and not strategy.strip()):
                raise ValueError("Strategy must be a non-empty string definition or None.")

        except (ValueError, TypeError) as validation_err:
            print(f"--- [ERROR] Validation error: {validation_err}")
            self.discovery_socket.send_json({"status": "error", "message": f"Validation failed: {validation_err}"})

        try:
            group_runtime_port = self.groups[group_id].config.communication_port

            p = multiprocessing.Process(
                target=run_model_worker_process, 
                args=(self._contexts[f"{group_id}.{_stream_config.source_name}"], group_runtime_port), 
                daemon=True)

            p.start()

            self.active_workers.append(p)
            
        except Exception as proc_err:
            print(f"--- [ERROR] Failed to start worker process: {proc_err}")
            self.discovery_socket.send_json({"status": "error", "message": f"Failed to start worker: {proc_err}"})

        try:
            self.discovery_socket.send_json({"status": "worker_spawned", "port": stream_port})
            print(f"--- [MANAGER] Started {strategy} worker for port {stream_port}")
        except zmq.ZMQError as send_err:
            print(f"--- [ERROR] Failed to send confirmation message: {send_err}")

    def shutdown_handler(self):
        print(f"--- [SYSTEM] Termination signal received. Cleaning up {len(self.active_workers)} workers...\n")
        for p in self.active_workers:
            try:
                if p.is_alive():
                    p.terminate()
                    p.join(timeout=2)

                    if p.is_alive():
                        print(f"--- [WARNING] Worker {p.pid} did not terminate gracefully. Forcing kill.")
                        p.kill()
                        p.join(timeout=1)

            except Exception as e:
                print(f"--- [ERROR] Exception while terminating worker {p.pid}: {e}")
                continue

        print("--- [SYSTEM] All processes cleared. Exit.")
        sys.exit(0)