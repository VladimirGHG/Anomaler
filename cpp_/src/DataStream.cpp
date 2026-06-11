#include "DataStream.h"
#include <nlohmann/json.hpp>
#include "telemetry_generated.h"
#include <type_traits>
#include <fstream>
#include <algorithm>
#include <iostream>
#include <sstream>

using json = nlohmann::json;

// DataStream class to manage a collection of SensorDataPoints
void DataStream::addDataPoint(const SensorDataPoint& dataPoint) {
    dataPoints.push_back(dataPoint);
}

SensorDataPoint DataStream::getDataPoint() {
    if (!dataPoints.empty()) {
        SensorDataPoint first = dataPoints.front(); 
        dataPoints.pop_front(); 
        return first; 
    }
    throw std::runtime_error("No data points available");
}

void DataStream::clear(int toRemove) {
    int actualRemove = std::min(toRemove, static_cast<int>(dataPoints.size()));
    for (int i = 0; i < actualRemove; ++i) {
        dataPoints.pop_front();
    }
}

std::string DataStream::toJson(bool pretty, long long limit) const {
    nlohmann::json j;
    size_t total = dataPoints.size();
    
    size_t count = (limit > 0 && (size_t)limit < total) ? (size_t)limit : total;
    j["count"] = count;
    j["datapoints"] = nlohmann::json::array();

    size_t start_idx = total - count;

    for (size_t i = start_idx; i < total; ++i) {
        nlohmann::json point;
        const auto& dp = dataPoints[i];
        
        std::visit([&](auto&& arg) { point["value"] = arg; }, dp.getValue());
        point["timestamp"] = dp.getTimestamp();
        point["shouldbeAnomaly"] = dp.getIsAnomaly();
        
        j["datapoints"].push_back(point);
    }

    return pretty ? j.dump(4) : j.dump();
}

std::vector<uint8_t> DataStream::toFlatBuffers(long long limit) const {
    size_t total = dataPoints.size();
    size_t count = (limit > 0 && (size_t)limit < total) ? (size_t)limit : total;
    size_t start_idx = total - count;

    // Allocate 1024 bytes upfront to limit dynamic memory allocations in the loop
    flatbuffers::FlatBufferBuilder builder(1024);
    
    // Store offsets of messages sequentially
    std::vector<flatbuffers::Offset<Anomaler::Serialization::TelemetryMessage>> messages_vector;
    messages_vector.reserve(count);

    for (size_t i = start_idx; i < total; ++i) {
        const auto& dp = dataPoints[i];
        std::cout << "[DEBUG] Processing DataPoint for FlatBuffers: " << dp << std::endl;
        double extracted_value = 0.0;
        std::visit([&](auto&& arg) { 
            using T = std::decay_t<decltype(arg)>; 
            
            if constexpr (std::is_same_v<T, std::string>) {
                try {
                    extracted_value = std::stod(arg);
                } catch (...) {
                    extracted_value = 0.0;
                }
            } else if constexpr (std::is_arithmetic_v<T>) {
                extracted_value = static_cast<double>(arg);
            }
        }, dp.getValue());

        // Timestamp extraction
        double extracted_timestamp = 0.0;
        try {
            std::tm tm = {};
            std::istringstream ss(dp.getTimestamp());
            ss >> std::get_time(&tm, "%Y-%m-%d %H:%M:%S");
            if (ss.fail()) {
                std::cout << "[DEBUG] get_time failed for: " << dp.getTimestamp() << std::endl;
            } else {
                double ms = 0.0;
                size_t dot = dp.getTimestamp().find('.');
                if (dot != std::string::npos) {
                    ms = std::stod(dp.getTimestamp().substr(dot));
                }
                tm.tm_isdst = -1;
                extracted_timestamp = static_cast<double>(std::mktime(&tm)) + ms;
                std::cout << "[DEBUG] Parsed timestamp: " << extracted_timestamp << std::endl;
            }
        } catch (...) {
            extracted_timestamp = 0.0;
        }

        // // Safe conversion for timestamps stored as string formats
        // try {
        //     extracted_timestamp = std::stod(dp.getTimestamp());
        // } catch (...) {
        //     extracted_timestamp = 0.0;
        // }

        // Directly construct the child table inside the builder's scratchpad memory
        auto message_offset = Anomaler::Serialization::CreateTelemetryMessage(
            builder, 
            extracted_timestamp, 
            extracted_value
        );
        messages_vector.push_back(message_offset);
    }

    // Wrap the entire batch inside a single TelemetryBatch array mapping
    auto batch_vector = builder.CreateVector(messages_vector);
    auto batch_root = Anomaler::Serialization::CreateTelemetryBatch(builder, batch_vector);
    
    builder.Finish(batch_root);

    // Return a single contiguous buffer with zero heap fragmentation
    uint8_t* buf = builder.GetBufferPointer();
    size_t size = builder.GetSize();
    
    return std::vector<uint8_t>(buf, buf + size);
}

// Export datapoints to JSON file for Python training
void DataStream::exportToJsonFile(const std::string& filename) const {
    std::ofstream file(filename);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + filename);
    }
    file << toJson(true, -1); 
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