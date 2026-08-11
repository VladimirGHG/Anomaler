#pragma once
#include <string>

struct GroupOptions {
    std::string group_id;
    std::string replicate;
    std::vector<std::string> connections;
    std::string file_path = "../configs/group_config.yaml";
    int pca_n_timestamps = 2000;
    double synchronization_frequency = 0.05;
};