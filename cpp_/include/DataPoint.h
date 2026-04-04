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

    DataValue getValue() const;
    std::string getTimestamp() const;

    friend std::ostream& operator<<(std::ostream& os, const SensorDataPoint& p);

private:
    DataValue value;
    std::string timestamp;

    static std::string getCurrentTime();
};

#endif