#pragma once
#include "GroupOptions.h"
#include <CLI/CLI.hpp>

// Registers the "group" subcommand on `app`. Currently takes no options --
// the group definition itself is still hardcoded inside run_group().
CLI::App* setup_group_command(CLI::App& app, GroupOptions& opts);

// Launches the predefined group of stream sources via SourceGroup.
int run_group(const GroupOptions& opts);