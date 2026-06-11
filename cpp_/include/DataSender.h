#ifndef DATASENDER_H
#define DATASENDER_H

#include <zmq.hpp>
#include <string>
#include "DataStream.h"

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

    enum class SerializationProtocol { JSON, FLATBUFFERS };    

    SerializationProtocol serialization_protocol;

    std::function<int(int, bool)> executor; // Function pointer to the appropriate send method based on serialization protocol
    int sendBatch(int batch_size, bool clear_after_send = true); // Unified method to send batches without conditional branches
    DataSender(const std::string& endpoint, SerializationProtocol protocol);
    int sendJson(int batch_size=1, bool clear_after_send=true);
    int sendBinary(int batch_size=1, bool clear_after_send=true);
};

#endif