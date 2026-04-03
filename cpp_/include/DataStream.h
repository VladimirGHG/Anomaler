#ifndef DATA_STREAM_H
#define DATA_STREAM_H

#include <vector>
#include <string>
#include <fstream>
#include <stdexcept>
#include "DataPoint.h"

class DataStream {
public:
    void addDataPoint(const SensorDataPoint& dataPoint);

    SensorDataPoint getDataPoint();

    std::string toJson() const;

    void exportToJsonFile(const std::string& filename) const;

    void exportToCsvFile(const std::string& filename) const;

private:
    std::vector<SensorDataPoint> dataPoints;

};

#endif