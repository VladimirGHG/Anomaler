#include "DataSender.h"
#include "DataStream.h"
#include "telemetry_generated.h"
#include <zmq.hpp>
#include <iostream>
#include <nlohmann/json.hpp>
#include <functional>
#include <thread>
#include <cstring>
#include <cstdlib>

DataSender::DataSender(const std::string& endpoint, SerializationProtocol protocol)
    : context(1), stream(), socket(context, zmq::socket_type::push), serialization_protocol(protocol) {
    
    socket.bind(endpoint);

    if (protocol == SerializationProtocol::FLATBUFFERS) {
        executor = [this](int b_size, bool clear) { 
            return this->sendBinary(b_size, clear); 
        };
    } else {
        executor = [this](int b_size, bool clear) { 
            return this->sendJson(b_size, clear); 
        };
    }
}

int DataSender::sendBatch(int batch_size, bool clear_after_send) {
    return executor(batch_size, clear_after_send);
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
    // else {
    //     std::cerr << "[ZMQ] Failed to send message. Retrying..." << std::endl;
    //     for (int attempt = 1; attempt <= 3; ++attempt) {
    //         std::this_thread::sleep_for(std::chrono::milliseconds(100 * attempt));
    //         result = socket.send(message, zmq::send_flags::none);
    //         if (result) {
    //             std::cout << "[ZMQ] Sent " << payload.size() << " bytes on retry attempt " << attempt << "." << std::endl;
    //             if (clear_after_send) {
    //                 stream.clear(batch_size);
    //             } break;
    //         }   
    //     }
    //     std::cerr << "[ZMQ] Failed to send message after 3 attempts." << std::endl;
    //     std::exit(EXIT_FAILURE); // Terminate the process if sending fails after retries
    // }
    std::cerr << "[ZMQ] Failed to send message." << std::endl;
    return 0;
}

int DataSender::sendBinary(int batch_size, bool clear_after_send) {
    if (batch_size <= 0) {
        batch_size = 1; 
    }

    std::vector<uint8_t> payload = stream.toFlatBuffers(batch_size);
    
    zmq::message_t message(payload.size());
    std::memcpy(message.data(), payload.data(), payload.size());
    auto result = socket.send(message, zmq::send_flags::none);

    if (result) {
        std::cout << "[ZMQ FlatBuffers] Sent unified batch of " << payload.size() << " bytes." << std::endl;
        if (clear_after_send) {
            stream.clear(batch_size);
        }
        return 1;
    }
    
    return 0;
}