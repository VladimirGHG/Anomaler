#ifndef DATASENDER_H
#define DATASENDER_H

#include <zmq.hpp>
#include <string>
#include <functional>
#include "DataStream.h"

/** @brief A class responsible for sending data streams over a ZeroMQ socket.
 * This class abstracts the network transmission layer. 
 * It connects to a specified endpoint and sends serialized data streams in JSON format.
 */
class DataSender {
private:
    zmq::context_t context;
public:
    DataStream stream;
    zmq::socket_t socket;

    enum class SerializationProtocol { JSON, FLATBUFFERS };    

    SerializationProtocol serialization_protocol;
    std::string source_name;
    
    int sendBatch(int batch_size, bool clear_after_send = true);
    DataSender(const std::string& endpoint, SerializationProtocol protocol, const std::string& source_name);
    int sendJson(int batch_size=1, bool clear_after_send=true);
    int sendBinary(int batch_size=1, bool clear_after_send=true);
};

#endif