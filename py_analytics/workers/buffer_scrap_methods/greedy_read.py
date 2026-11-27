from typing import Literal

import zmq

def greedy_read(receiver, func) -> tuple[list[dict], Literal[0, 1]]:
    """
    Greedy read from a ZeroMQ receiver socket.
    
    Parameters:
        receiver: A ZeroMQ receiver socket from which to read messages.
        func: A function that processes the raw message and returns a packet.
        
    Returns:
        A tuple containing all decoded packets and a status code:
        - The first element is a list of decoded packets.
        - The second element is a status code (0 or 1):
            - 0 indicates that a packet was successfully processed.
            - 1 indicates that no packets were processed (queue was empty).
    """
    packets = []
    while True:
        try:
            raw = receiver.recv(flags=zmq.NOBLOCK)
            packet = func(raw)

            if packet:
                packets.append(packet)
        
        except zmq.Again:
            return packets, 0 if packets else 1
