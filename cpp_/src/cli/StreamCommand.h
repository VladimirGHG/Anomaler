#pragma once
#include <CLI/CLI.hpp>
#include "StreamOptions.h"

// Registers the "stream" subcommand's options on `app`, writing parsed
// values into `opts` on parse. Call app.parse(...) after this, then check
// app.got_subcommand(the returned pointer) before calling run_stream().
CLI::App* setup_stream_command(CLI::App& app, StreamOptions& opts);

// Runs the stream: manager handshake, sender setup, then the polling loop.
// Returns the process exit code.
int run_stream(const StreamOptions& opts);