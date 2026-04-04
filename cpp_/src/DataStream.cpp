#include "DataStream.h"
#include <nlohmann/json.hpp>

// DataStream class to manage a collection of SensorDataPoints
void DataStream::addDataPoint(const SensorDataPoint& dataPoint) {
    dataPoints.push_back(dataPoint);
}

SensorDataPoint DataStream::getDataPoint() {
    if (!dataPoints.empty()) {
        SensorDataPoint last = dataPoints.back();
        dataPoints.pop_back();
        return last; 
    }
    throw std::runtime_error("No data points available");
}

// Convert datapoints to JSON format
using json = nlohmann::json;

std::string DataStream::toJson() const {
    json j;
    j["count"] = dataPoints.size();
    
    for (const auto& dp : dataPoints) {
        json point;
        std::visit([&](auto&& arg) { point["value"] = arg; }, dp.getValue());
        point["timestamp"] = dp.getTimestamp();
        j["datapoints"].push_back(point);
    }

    return j.dump(4);
}

// Export datapoints to JSON file for Python training
void DataStream::exportToJsonFile(const std::string& filename) const {
    std::ofstream file(filename);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + filename);
    }
    file << toJson();
    file.close();
}

// Export datapoints to CSV file for Python training
void DataStream::exportToCsvFile(const std::string& filename) const {
    std::ofstream file(filename);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + filename);
    }

    file << "value,timestamp\n";
    for (const auto& dataPoint : dataPoints) {
        json val;
        std::visit([&](auto&& arg) { val = arg; }, dataPoint.getValue());

        file << val.dump() << ",";
        file << "\"" << dataPoint.getTimestamp() << "\"\n";
    }
    file.close();
}