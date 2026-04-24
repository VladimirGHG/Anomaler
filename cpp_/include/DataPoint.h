#ifndef SENSOR_DATA_POINT_H
#define SENSOR_DATA_POINT_H

#include <string>
#include <iostream>
#include "DataTypes.h"

/** @brief A class representing a single data point from a sensor.
 * Each data point consists of a value (which can be of various types as defined in DataTypes.h) and a timestamp.
 * The class provides functionality to get the current time in a human-readable format and to print the data point for debugging purposes.
 */
class SensorDataPoint {
public:
    SensorDataPoint(DataValue value, std::string timestamp = getCurrentTime());
    SensorDataPoint(DataValue value, bool isAnomaly, std::string timestamp = getCurrentTime());
    DataValue getValue() const;
    std::string getTimestamp() const;
    bool getIsAnomaly() const;

    friend std::ostream& operator<<(std::ostream& os, const SensorDataPoint& p);
    static std::string getCurrentTime();

private:
    DataValue value;
    bool isAnomaly; // Flag indicating if a data point is an anomaly, can be used for future extensions
    std::string timestamp;

};

#endif