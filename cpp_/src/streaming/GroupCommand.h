#pragma once
#include <CLI/CLI.hpp>

// Registers the "group" subcommand on `app`. Currently takes no options --
// the group definition itself is still hardcoded inside run_group().
CLI::App* setup_group_command(CLI::App& app);

// Launches the predefined group of stream sources via SourceGroup.
// Returns the process exit code.
int run_group();