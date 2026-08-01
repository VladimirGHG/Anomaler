#include "DataSenderFactory.h"
#include <algorithm>
#include <cctype>

DataSender::SerializationProtocol parseProtocol(std::string str) {
    std::transform(str.begin(), str.end(), str.begin(), ::toupper);
    
    if (str == "FLATBUFFERS") { return DataSender::SerializationProtocol::FLATBUFFERS; }
    return DataSender::SerializationProtocol::JSON;
}

DataSender build_data_sender(const StreamOptions& opts) {
    DataSender data_sender("tcp://127.0.0.1:" + std::to_string(opts.port), parseProtocol(opts.serialization));

    data_sender.socket.set(zmq::sockopt::sndtimeo, 10'000);
    data_sender.socket.set(zmq::sockopt::sndhwm, 10);
    data_sender.socket.set(zmq::sockopt::immediate, 1);
    data_sender.socket.set(zmq::sockopt::linger, 0);

    return data_sender;
}