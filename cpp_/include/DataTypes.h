#ifndef DATA_TYPES_H
#define DATA_TYPES_H

#include <variant>
#include <vector>
#include <string>

/** @brief A variant type representing different possible data values. 
 * Those are the types supported for the usage, and can be added to the DataStreams */
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