#ifndef DATASENDER_H
#define DATASENDER_H

#include <zmq.hpp>
#include <string>
#include "DataStream.h"

enum class SerializationProtocol {
    BINARY,
    JSON
};

/** @brief A class responsible for sending data streams over a ZeroMQ socket.
 * This class abstracts the network transmission layer. 
 * It connects to a specified endpoint and sends serialized data streams in JSON format.
 */
class DataSender {
private:
    zmq::context_t context;
public:
    DataStream stream; // Made public for direct access in main.cpp, but can be refactored to use getter/setter if needed
    zmq::socket_t socket;
    SerializationProtocol serialization_protocol;
    explicit DataSender(const std::string& endpoint, DataStream& stream, SerializationProtocol protocol = SerializationProtocol::JSON);
    explicit DataSender(const std::string& endpoint = "tcp://127.0.0.1:5555", SerializationProtocol protocol = SerializationProtocol::JSON);
    int sendJson(int batch_size=1, bool clear_after_send=true);
    int sendBinary(int batch_size=1, bool clear_after_send=true);
};

#endif