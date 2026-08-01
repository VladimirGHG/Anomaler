#pragma once
#include <zmq.hpp>
#include "StreamOptions.h"

// Registers this stream with the manager process over a ZMQ REQ/REP
// handshake and blocks (up to a timeout) for its acknowledgment.
// Returns true on success, false on timeout/connection failure.
bool perform_manager_handshake(zmq::context_t& context, const StreamOptions& opts);