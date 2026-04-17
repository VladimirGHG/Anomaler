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
    void addDataPoint(const SensorDataPoint& dataPoint);

    SensorDataPoint getDataPoint();

    void clear(int toRemove = -1);

    std::string toJson(bool pretty=false, long long limit=-1) const;

    void exportToJsonFile(const std::string& filename) const;

    void exportToCsvFile(const std::string& filename) const;
    std::deque<SensorDataPoint> dataPoints;
};

#endif