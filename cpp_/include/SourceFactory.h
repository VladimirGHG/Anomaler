#ifndef SOURCEFACTORY_H
#define SOURCEFACTORY_H

#include <memory>
#include <string>
#include <vector>
#include "DataSource.h"

/**
 * @class SourceFactory
 * @brief Static factory for creating data generation strategies.
 * * This class follows the Factory Pattern to decouple the creation of
 * sources from the execution of the data stream.
 */
class SourceFactory {
public:
    /**
     * @brief Creates a unique instance of a DataSource.
     * @param mode The type of source (random, outlier, drift).
     * @return std::unique_ptr<DataSource> The requested source object.
     */
    static const std::vector<std::string> GetAvailableModes();

    static std::unique_ptr<DataSource> create(
        const std::string& mode, 
        const std::string& data_mode,
        const std::string& port = "", 
        const std::string& sensor_name = "default_sensor");
};

#endif