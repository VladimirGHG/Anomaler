#include "DataSender.h"
#include "DataStream.h"
#include <iostream>
#include <nlohmann/json.hpp>

DataSender::DataSender(const std::string& endpoint, DataStream& stream)
    : context(1), stream(stream), socket(context, zmq::socket_type::push) {
    socket.bind(endpoint);
}
DataSender::DataSender(const std::string& endpoint)
    : context(1), stream(DataStream()), socket(context, zmq::socket_type::push) {
    socket.bind(endpoint);
}
int DataSender::send(int batch_size, bool clear_after_send) {
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
