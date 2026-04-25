#include "sources/SerialSensorSource.h"
#include <regex>
#include <iostream>
#include <thread>
#include <chrono>

SerialSensorSource::SerialSensorSource(const std::string& port_name, const std::string& sensor_name) {
    if (sp_get_port_by_name(port_name.c_str(), &port) != SP_OK) {
        throw std::runtime_error("Could not find serial port: " + port_name);
    }

    if (sp_open(port, SP_MODE_READ) != SP_OK) {
        throw std::runtime_error("Could not open serial port: " + port_name);
    }

    sp_set_baudrate(port, 9600);
    sp_set_bits(port, 8);
    sp_set_parity(port, SP_PARITY_NONE);
    sp_set_stopbits(port, 1);
    
    std::cout << "Connected to sensor: " << sensor_name << " on " << port_name << std::endl;

    sp_flush(port, SP_BUF_BOTH); 
    
    // Give Arduino 2 seconds to finish its boot sequence
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));
}

SerialSensorSource::~SerialSensorSource() {
    if (port) {
        sp_close(port);
        sp_free_port(port);
    }

    sp_flush(port, SP_BUF_BOTH); 
    
    // Give Arduino 2 seconds to finish its boot sequence
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));
}

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