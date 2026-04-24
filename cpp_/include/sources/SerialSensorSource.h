#ifndef SERIALSENSORSOURCE_H
#define SERIALSENSORSOURCE_H

#include "DataSource.h"
#include "DataPoint.h"
#include <libserialport.h>

class SerialSensorSource : public DataSource {
public:
    SerialSensorSource(const std::string& port_name, const std::string& sensor_type);
    ~SerialSensorSource();
    
    SensorDataPoint getNextValue() override;

private:
    struct sp_port* port;
    std::string type;
};

#endif