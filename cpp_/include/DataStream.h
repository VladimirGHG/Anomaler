#ifndef DATA_STREAM_H
#define DATA_STREAM_H

#include <vector>
#include <string>
#include <fstream>
#include <stdexcept>
#include "DataPoint.h"
#include <deque>

/** @brief A class representing a stream of sensor data points.
 * This class manages a collection of DataPoints, allowing for adding new points,
 * retrieving points, and exporting the stream to JSON or CSV formats for further processing in other applications/systems.
*/
class DataStream {
public:
    DataStream() : next_batch_id(0) {}
    void addDataPoint(const SensorDataPoint& dataPoint);

    SensorDataPoint getDataPoint();
    uint64_t next_batch_id;
    void clear(int toRemove = -1);

    std::string toJson(bool pretty=false, long long limit=-1) const;
    std::vector<uint8_t> toFlatBuffers(long long limit) const;
    
    void exportToJsonFile(const std::string& filename) const;

    void exportToCsvFile(const std::string& filename) const;
    std::deque<SensorDataPoint> dataPoints;
};

#endif