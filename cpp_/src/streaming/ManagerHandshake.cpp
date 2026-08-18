#include "ManagerHandshake.h"
#include <nlohmann/json.hpp>

namespace {
constexpr const char* kManagerEndpoint = "tcp://localhost:5555";
constexpr int kHandshakeTimeoutMs = 60'000;
}

bool perform_manager_handshake(zmq::context_t& context, const StreamOptions& opts) {
    zmq::socket_t announcer(context, zmq::socket_type::req);
    announcer.connect(kManagerEndpoint);

    nlohmann::json registration = {
        {"action", "register_stream"},
        {"port", opts.port},
        {"model", opts.source_type},
        {"mode", opts.data_mode},
        {"ml_model", opts.ml_model},
        {"serialization", opts.serialization},
        {"source_name", opts.source_name},
        {"group_id", opts.group_id}
    };

    announcer.set(zmq::sockopt::linger, 0);
    announcer.set(zmq::sockopt::sndtimeo, kHandshakeTimeoutMs);
    announcer.set(zmq::sockopt::rcvtimeo, kHandshakeTimeoutMs);
    announcer.send(zmq::buffer(registration.dump()), zmq::send_flags::none);

    zmq::message_t reply;
    auto handshake_res = announcer.recv(reply, zmq::recv_flags::none);
    return static_cast<bool>(handshake_res);
}