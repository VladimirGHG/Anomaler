#include "DataSender.h"
#include <iostream>

DataSender::DataSender(const std::string& endpoint) 
    : context(1), socket(context, zmq::socket_type::push) {
    socket.connect(endpoint);
}

void DataSender::send(const DataStream& stream) {
    std::string payload = stream.toJson();
    
    zmq::message_t message(payload.size());
    memcpy(message.data(), payload.c_str(), payload.size());
    
    auto result = socket.send(message, zmq::send_flags::none);
    if (result) {
        std::cout << "[ZMQ] Sent " << stream.toJson().size() << " bytes." << std::endl;
    }
}