#include "DataSender.h"
#include "DataStream.h"
#include "telemetry_generated.h"
#include <zmq.hpp>
#include <iostream>
#include <nlohmann/json.hpp>

DataSender::DataSender(const std::string& endpoint, DataStream& stream, SerializationProtocol protocol)
    : context(1), stream(stream), socket(context, zmq::socket_type::push), serialization_protocol(protocol) {
    socket.bind(endpoint);
}
DataSender::DataSender(const std::string& endpoint, SerializationProtocol protocol)
    : context(1), stream(DataStream()), socket(context, zmq::socket_type::push), serialization_protocol(protocol) {
    socket.bind(endpoint);
}
int DataSender::sendJson(int batch_size, bool clear_after_send) {
    if (batch_size <= 0) {
        batch_size = 1; // Ensure batch size is at least 1
    }

    // Convert the data stream to JSON format for sending
    std::string payload = stream.toJson(false, batch_size);
    
    zmq::message_t message(payload.size());
    memcpy(message.data(), payload.c_str(), payload.size());
    
    auto result = socket.send(message, zmq::send_flags::none);
    if (result) {
        std::cout << "[ZMQ] Sent " << payload.size() << " bytes." << std::endl;
        if (clear_after_send) {
            stream.clear(batch_size);
        }
        return 1;
    }
    return 0;
}

int DataSender::sendBinary(int batch_size, bool clear_after_send) {
    if (batch_size <= 0) {
        batch_size = 1; 
    }

    std::vector<std::vector<uint8_t>> payloads = stream.toFlatBuffers(batch_size);
    
    int successful_sends = 0;

    for (const auto& payload : payloads) {
        zmq::message_t message(payload.size());
        std::memcpy(message.data(), payload.data(), payload.size());
        
        auto result = socket.send(message, zmq::send_flags::none);
        if (result) {
            successful_sends++;
        }
    }

    if (successful_sends > 0) {
        std::cout << "[ZMQ FlatBuffers] Sent " << successful_sends << " discrete telemetry frames." << std::endl;
        if (clear_after_send) {
            stream.clear(batch_size);
        }
        return 1;
    }
    
    return 0;
}
