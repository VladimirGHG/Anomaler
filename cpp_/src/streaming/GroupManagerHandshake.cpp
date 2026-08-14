#include "streaming/GroupManagerHandshake.h"
#include "GroupOptions.h"

#include <nlohmann/json.hpp>
#include <iostream>

namespace {

constexpr const char* kManagerEndpoint = "tcp://localhost:5555";
constexpr int kHandshakeTimeoutMs = 60'000;

}

bool perform_group_manager_handshake(zmq::context_t& context, const GroupOptions& opts) {
        
    try {
        zmq::socket_t announcer(context, zmq::socket_type::req);

        announcer.set(zmq::sockopt::linger, 0);
        announcer.set(zmq::sockopt::sndtimeo, kHandshakeTimeoutMs);
        announcer.set(zmq::sockopt::rcvtimeo, kHandshakeTimeoutMs);
        announcer.connect(kManagerEndpoint);

        nlohmann::json registration = {
            {"action", "register_group"},
            {"group_id", opts.group_id},

            {
                "synchronization",
                {
                    {"frequency", opts.synchronization_frequency}
                }
            },

            {
                "virtual_sensor",
                {
                    {"target", opts.target},
                    {"connections", opts.connections},
                    {"pca_n_timestamps", opts.pca_n_timestamps}
                }
            }
        };

        std::cout << "[GROUP MANAGER] Registering group '" << opts.group_id << "' with Python Manager..." << std::endl;
        auto send_result = announcer.send(zmq::buffer(registration.dump()), zmq::send_flags::none);

        if (!send_result) {
            std::cerr << "[GROUP MANAGER] Failed to send group registration." << std::endl;

            return false;
        }

        zmq::message_t reply;
        auto recv_result = announcer.recv(reply, zmq::recv_flags::none);

        if (!recv_result) {
            std::cerr << "[GROUP MANAGER] Python Manager did not respond." << std::endl;

            return false;
        }

        std::string response(static_cast<const char*>(reply.data()), reply.size());
        std::cout << "[GROUP MANAGER] Received: " << response << std::endl;
        nlohmann::json response_json = nlohmann::json::parse(response);
        const std::string status = response_json.value("status", "");

        if (status != "group_registered") {
            std::cerr << "[GROUP MANAGER] Group registration rejected." << std::endl;

            return false;
        }

        std::cout
            << "[GROUP MANAGER] Group '"
            << opts.group_id
            << "' registered successfully."
            << std::endl;

        return true;
    }
    catch (const zmq::error_t& e) {
        std::cerr
            << "[GROUP MANAGER] ZMQ error: "
            << e.what()
            << std::endl;

        return false;
    }
    catch (const nlohmann::json::exception& e) {
        std::cerr
            << "[GROUP MANAGER] Invalid JSON response: "
            << e.what()
            << std::endl;

        return false;
    }
    catch (const std::exception& e) {
        std::cerr
            << "[GROUP MANAGER] Handshake error: "
            << e.what()
            << std::endl;

        return false;
    }
}