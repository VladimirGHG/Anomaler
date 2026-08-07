#include "sources/SerialSensorSource.h"
#include <regex>
#include <iostream>
#include <thread>
#include <chrono>

SerialSensorSource::SerialSensorSource(const std::string& port_name, const std::string& sensor_name)
    : type(sensor_name)
{
    port.init(port_name.c_str(),
            9600,
            itas109::ParityNone,
            itas109::DataBits8,
            itas109::StopOne,
            itas109::FlowNone);

    port.setOperateMode(itas109::SynchronousOperate);

    if (!port.open()) {
        throw std::runtime_error("Could not open serial port: " + port_name);
    }

    std::cout << "Connected to sensor: " << sensor_name << " on " << port_name << std::endl;

    std::this_thread::sleep_for(std::chrono::milliseconds(2000));
}

SerialSensorSource::~SerialSensorSource() {
    if (port.isOpen()) {
        port.close();
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(2000));
}

SensorDataPoint SerialSensorSource::getNextValue() {
    char buffer[512];
    int bytes = 0;

    const int timeout_ms = 2000;
    const int poll_interval_ms = 50;
    int waited = 0;

    while (waited < timeout_ms) {
        bytes = port.readData(buffer, 511);
        if (bytes > 0) break;
        std::this_thread::sleep_for(std::chrono::milliseconds(poll_interval_ms));
        waited += poll_interval_ms;
    }

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