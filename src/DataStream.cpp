#include "DataStream.h"

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

// Convert datapoints to JSON format (Python-compatible)
std::string DataStream::toJson() const {
    std::string json = "{\n";
    json += "  \"datapoints\": [\n";
    for (size_t i = 0; i < dataPoints.size(); ++i) {
        json += "    {\n";
        json += "      \"value\": ";
        json += dataValueToJson(dataPoints[i].getValue());
        json += ",\n";
        json += "      \"timestamp\": \"" + dataPoints[i].getTimestamp() + "\"\n";
        json += "    }";
        if (i + 1 < dataPoints.size()) json += ",";
        json += "\n";
    }
    json += "  ],\n";
    json += "  \"count\": " + std::to_string(dataPoints.size()) + "\n";
    json += "}";
    return json;
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
        file << dataValueToJson(dataPoint.getValue()) << ",";
        file << "\"" << dataPoint.getTimestamp() << "\"\n";
    }
    file.close();
}

std::vector<SensorDataPoint> dataPoints;

// Helper function to convert DataValue to JSON string
std::string DataStream::dataValueToJson(const DataValue& value) {
    std::string result;
    std::visit([&](auto&& arg) {
        if constexpr (std::is_same_v<std::decay_t<decltype(arg)>, std::vector<int>> ||
                    std::is_same_v<std::decay_t<decltype(arg)>, std::vector<float>> ||
                    std::is_same_v<std::decay_t<decltype(arg)>, std::vector<double>> ||
                    std::is_same_v<std::decay_t<decltype(arg)>, std::vector<std::string>>) {
            result += "[";
            for (size_t i = 0; i < arg.size(); ++i) {
                if constexpr (std::is_same_v<std::decay_t<decltype(arg)>, std::vector<std::string>>) {
                    result += "\"" + arg[i] + "\"";
                } else {
                    result += std::to_string(arg[i]);
                }
                if (i + 1 < arg.size()) result += ", ";
            }
            result += "]";
        } else if constexpr (std::is_same_v<std::decay_t<decltype(arg)>, std::string>) {
            result += "\"" + arg + "\"";
        } else {
            result += std::to_string(arg);
        }
    }, value);
    return result;
};