#pragma once

#include <zmq.hpp>
#include <string>

bool perform_group_manager_handshake(
    zmq::context_t& context,
    const std::string& group_id,
    const std::string& synchronization_mode,
    double synchronization_frequency,
    int calibration_samples
);