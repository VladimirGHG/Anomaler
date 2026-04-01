#include <iostream>
#include <string>
#include <vector>
#include <chrono>
#include <ctime>
#include <sstream>
#include <iomanip>

// SensorDataPoint class to represent a single data point from a sensor
template <typename T>
class SensorDataPoint {
public:
    SensorDataPoint(T value, std::string timestamp)
        : value(value), timestamp(timestamp) {}

    SensorDataPoint(T value) : value(value), timestamp(getCurrentTime()) {}

    SensorDataPoint() : value(T()), timestamp(getCurrentTime()) {}

    friend std::ostream& operator<<(std::ostream& os, const SensorDataPoint& p) {
        os << "value=" << p.value << ", timestamp=" << p.timestamp;
        return os;
    }

    T getValue() const { return value; }
    std::string getTimestamp() const { return timestamp; }

private:
    T value;
    std::string timestamp;

    static std::string getCurrentTime() {
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
};

// ---
class AnomalyDetector {
public:
    AnomalyDetector(double threshold) : threshold(threshold) {}

private:
    double threshold;
};

// DataStream class to manage a collection of SensorDataPoints
template <typename T>
class DataStream {
public:
    void addDataPoint(SensorDataPoint<T>& dataPoint) {
        dataPoints.push_back(dataPoint);
    }

    SensorDataPoint<T> getDataPoint() {
        if (!dataPoints.empty()) {
            SensorDataPoint<T> last = dataPoints.back();
            dataPoints.pop_back();
            return last; 
        }
        throw std::runtime_error("No data points available");
    }

private:
    std::vector<SensorDataPoint<double>> dataPoints;
};

// ---
int main() {
    SensorDataPoint<double> data1 = SensorDataPoint<double>(25.5);
    SensorDataPoint<double> data2 = SensorDataPoint<double>(30.0);
    DataStream<double> dataStream;
    dataStream.addDataPoint(data1);
    dataStream.addDataPoint(data2);
    std::cout << dataStream.getDataPoint() << "\n" << dataStream.getDataPoint() << std::endl;

    return 0;
}