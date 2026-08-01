#include "GroupCommand.h"
#include "SourceGroup.h"
#include <iostream>
#include <unordered_map>

CLI::App* setup_group_command(CLI::App& app) {
    return app.add_subcommand("group", "Launch a predefined group of stream sources");
}

int run_group() {
    std::cout << "[INFO] Launching Source Group..." << std::endl;

    std::unordered_map<std::string, FieldMap> group = {
        {{"source1"}, {{"source_type", "random"},  {"port", 5554}, {"frequency", 0.05}, {"ml_model", "SKlearnIsolatedForest"}, {"data_mode", "default"}, {"serialization", "json"}, {"batch_size", 40}, {"verbose", true}}},
        {{"source2"}, {{"source_type", "outlier"}, {"port", 5556}, {"frequency", 0.05}, {"ml_model", "SKlearnIsolatedForest"}, {"data_mode", "default"}, {"serialization", "json"}, {"batch_size", 40}, {"verbose", false}}},
        {{"source3"}, {{"source_type", "outlier"}, {"port", 5557}, {"frequency", 0.1},  {"ml_model", "SKlearnIsolatedForest"}, {"data_mode", "default"}, {"serialization", "json"}, {"batch_size", 40}, {"verbose", false}}}
    };

    SourceGroup sourceGroup(group);
    sourceGroup.launch();
    
    return 0;
}