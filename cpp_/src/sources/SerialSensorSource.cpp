#include "sources/SerialSensorSource.h"
#include <regex>

SensorDataPoint SerialSensorSource::getNextValue() {
    char buffer[512];
    int bytes = sp_blocking_read_next(port, buffer, 511, 2000); 
    
    if (bytes > 0) {
        buffer[bytes] = '\0';
        std::string raw(buffer);
        
        std::smatch match;
        std::regex val_regex("[-+]?[0-9]*\\.?[0-9]+");
        
        if (std::regex_search(raw, match, val_regex)) {
            return SensorDataPoint(std::stod(match.str()));
        }
    }
    return SensorDataPoint(0.0);
}