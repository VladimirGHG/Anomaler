#pragma once
#include <string>

struct StreamOptions {
    int port = 5555;
    double frequency = 0.05;
    int limit = 0;
    int batch_size = 50;
    std::string source_type = "random";
    std::string data_mode = "default";
    std::string ml_model = "SKlearnIsolatedForest";
    std::string readport;
    std::string source_name;
    std::string serialization = "json";
    std::string group_name;
    bool verbose = false;
};