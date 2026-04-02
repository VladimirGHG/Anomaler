#ifndef SENSOR_DATA_POINT_H
#define SENSOR_DATA_POINT_H

#include <string>
#include <iostream>
#include "DataTypes.h"

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