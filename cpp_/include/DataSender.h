#ifndef DATASENDER_H
#define DATASENDER_H

#include <zmq.hpp>
#include <string>
#include "DataStream.h"

class DataSender {
private:
    zmq::context_t context;
    zmq::socket_t socket;

public:
    DataSender(const std::string& endpoint = "tcp://127.0.0.1:5555");
    void send(const DataStream& stream);
};

#endif