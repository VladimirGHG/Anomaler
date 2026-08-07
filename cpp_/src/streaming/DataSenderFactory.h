#pragma once
#include <string>
#include "DataSender.h"
#include "StreamOptions.h"

// Parses the --serialization CLI string into the DataSender enum.
// Unrecognized values default to JSON.
DataSender::SerializationProtocol parseProtocol(std::string str);

// Builds a DataSender for `opts` with its socket options configured
DataSender build_data_sender(const StreamOptions& opts);