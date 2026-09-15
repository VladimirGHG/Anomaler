#pragma once

#include <string>
#include <vector>

struct GroupOptions {
    std::string group_id;
    std::string target;
    std::vector<std::string> connections;
    std::string file_path = "../config/group_config.yaml";
    int pca_n_timestamps = 2000;
    double synchronization_frequency = 0.05;
    std::string communication_host = "127.0.0.1";
    std::vector<int> communication_port_range = {5560, 5565};
};