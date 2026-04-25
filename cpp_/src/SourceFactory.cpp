#include "SourceFactory.h"
#include "sources/RandomSource.h"
#include "sources/OutlierSource.h"
#include "sources/DriftDecorator.h"
#include "sources/SerialSensorSource.h"
#include <algorithm>

std::unique_ptr<DataSource> SourceFactory::create(
    const std::string& mode, 
    const std::string& data_mode, 
    const std::string& port_name, 
    const std::string& sensor_name) 
    {
    
    std::unique_ptr<DataSource> model;
    if (mode == "outlier") {
        model = std::make_unique<OutlierSource>();
    } else if (mode == "random") {
        model = std::make_unique<RandomSource>();
    } else if (mode == "serial") {
        model = std::make_unique<SerialSensorSource>(port_name, sensor_name);
    }
    // Add more modes here as needed to create different types of data sources, such as "temperature", "pressure", etc.

    if (data_mode == "drift") {
        model = std::make_unique<DriftDecorator>(std::move(model), 0.01 /* drift magnitude */ );
    }

    return model;
}

const std::vector<std::string> SourceFactory::GetAvailableModes() {
    return {"random", "outlier", "serial"};
}