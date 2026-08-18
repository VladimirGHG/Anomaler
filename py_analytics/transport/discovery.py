import zmq

def create_discovery_socket(context: zmq.Context, port: int) -> zmq.Socket:
    try:
        socket = context.socket(zmq.REP)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, 1000)
        socket.bind(f"tcp://127.0.0.1:{port}")

        return socket

    except zmq.ZMQError:
        context.destroy()
        raise