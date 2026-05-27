#include "DataStream.h"
#include <nlohmann/json.hpp>
#include "telemetry_generated.h"
#include <type_traits>

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

void DataStream::clear(int toRemove) {
    int actualRemove = std::min(toRemove, static_cast<int>(dataPoints.size()));
    for (int i = 0; i < actualRemove; ++i) {
        dataPoints.pop_front();
    }
}

using json = nlohmann::json;

std::string DataStream::toJson(bool pretty, long long limit) const {
    nlohmann::json j;
    size_t total = dataPoints.size();
    
    // Calculate how many we actually send
    size_t count = (limit > 0 && (size_t)limit < total) ? (size_t)limit : total;
    j["count"] = count;
    j["datapoints"] = nlohmann::json::array();

    // Start index: 
    size_t start_idx = total - count;

    // Standard Forward Loop (Chronological Order)
    for (size_t i = start_idx; i < total; ++i) {
        nlohmann::json point;
        const auto& dp = dataPoints[i];
        
        std::visit([&](auto&& arg) { point["value"] = arg; }, dp.getValue());
        point["timestamp"] = dp.getTimestamp();
        point["shouldbeAnomaly"] = dp.getIsAnomaly();
        
        j["datapoints"].push_back(point);
        std::cout << point << std::endl;
    }

    return pretty ? j.dump(4) : j.dump();
}

std::vector<std::vector<uint8_t>> DataStream::toFlatBuffers(long long limit) const {
    std::vector<std::vector<uint8_t>> serialized_messages;
    size_t total = dataPoints.size();
    
    size_t count = (limit > 0 && (size_t)limit < total) ? (size_t)limit : total;
    size_t start_idx = total - count;

    for (size_t i = start_idx; i < total; ++i) {
        const auto& dp = dataPoints[i];
        
        double extracted_value = 0.0;
        std::visit([&](auto&& arg) { 
            using T = std::decay_t<decltype(arg)>; 
            
            if constexpr (std::is_same_v<T, std::string>) {
                extracted_value = std::stod(arg);
            }
        }, dp.getValue());
        double extracted_timestamp = std::stod(dp.getTimestamp());

        flatbuffers::FlatBufferBuilder builder(64);
        auto message_offset = Anomaler::Serialization::CreateTelemetryMessage(
            builder, 
            extracted_timestamp, 
            extracted_value
        );
        builder.Finish(message_offset);

        uint8_t* buf = builder.GetBufferPointer();
        size_t size = builder.GetSize();
        
        serialized_messages.push_back(std::vector<uint8_t>(buf, buf + size));
    }

    return serialized_messages;
}

// Export datapoints to JSON file for Python training
void DataStream::exportToJsonFile(const std::string& filename) const {
    std::ofstream file(filename);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + filename);
    }
    file << toJson(true, -1); // Export all data points in pretty format
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