#define CLI11_HAS_FILESYSTEM 0
#include <CLI/CLI.hpp>
#include <iostream>

#include "StreamOptions.h"
#include "StreamCommand.h"
#include "GroupCommand.h"
#include "GroupOptions.h"

int main(int argc, char** argv) {
    CLI::App app{"Anomaler: High-Performance Data Producer for ML Pipelines"};

    bool verbose = false;
    app.add_flag("-v,--verbose", verbose, "Enable detailed console logging");

    StreamOptions stream_opts;
    GroupOptions group_opts;
    auto* stream_cmd = setup_stream_command(app, stream_opts);
    auto* group_cmd = setup_group_command(app, group_opts);

    try {
        app.parse(argc, argv);
    } catch (const CLI::ParseError& e) {
        return app.exit(e);
    }

    if (app.got_subcommand(stream_cmd)) {
        stream_opts.verbose = stream_opts.verbose || verbose;
        return run_stream(stream_opts);
    }

    if (app.got_subcommand(group_cmd)) {
        return run_group(group_opts);
    }

    std::cout << app.help() << std::endl;
    return 0;
}