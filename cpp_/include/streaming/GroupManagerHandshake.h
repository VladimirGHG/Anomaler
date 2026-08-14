#pragma once

#include "GroupOptions.h"

#include <zmq.hpp>
#include <string>

bool perform_group_manager_handshake(zmq::context_t& context, const GroupOptions& opts);