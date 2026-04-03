#ifndef DATA_TYPES_H
#define DATA_TYPES_H

#include <variant>
#include <vector>
#include <string>

using DataValue = std::variant<
    int,
    float,
    double,
    std::string,
    std::vector<int>,
    std::vector<float>,
    std::vector<double>,
    std::vector<std::string>
>;

#endif