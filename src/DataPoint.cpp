#include "DataPoint.h"
#include <chrono>
#include <ctime>
#include <sstream>
#include <iomanip>

SensorDataPoint::SensorDataPoint(DataValue value, std::string timestamp)
    : value(value), timestamp(timestamp) {}

DataValue SensorDataPoint::getValue() const {
    return value;
}

std::string SensorDataPoint::getTimestamp() const {
    return timestamp;
}

std::string SensorDataPoint::getCurrentTime() {
    auto now = std::chrono::system_clock::now();
    auto now_ms = std::chrono::time_point_cast<std::chrono::milliseconds>(now);

    auto epoch = now_ms.time_since_epoch();
    long ms = epoch.count() % 1000;

    std::time_t now_c = std::chrono::system_clock::to_time_t(now);
    std::tm* tm = std::localtime(&now_c);

    std::ostringstream oss;
    oss << std::put_time(tm, "%Y-%m-%d %H:%M:%S") << "." << ms;
    return oss.str();
}

std::ostream& operator<<(std::ostream& os, const SensorDataPoint& p) {
    os << "value=";

    std::visit([&](auto&& arg) {
        using T = std::decay_t<decltype(arg)>;

        if constexpr (
            std::is_same_v<T, std::vector<int>> ||
            std::is_same_v<T, std::vector<float>> ||
            std::is_same_v<T, std::vector<double>> ||
            std::is_same_v<T, std::vector<std::string>>
        ) {
            os << "[";
            for (size_t i = 0; i < arg.size(); ++i) {
                os << arg[i];
                if (i + 1 < arg.size()) os << ", ";
            }
            os << "]";
        } else {
            os << arg;
        }
    }, p.value);

    os << ", timestamp=" << p.timestamp;
    return os;
}