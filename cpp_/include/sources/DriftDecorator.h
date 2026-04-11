#ifndef SOURCES_DRIFTSOURCE_H
#define SOURCES_DRIFTSOURCE_H

#include "DataSource.h"
#include <random>

/** @brief A concrete implementation of DataSource that simulates sensor drift over time.
 * This class models a scenario where the sensor's readings gradually deviate from the true value, 
 * which is common in real-world sensors due to wear and tear or environmental factors.
 */
class DriftDecorator : public DataSource {
private:
    std::unique_ptr<DataSource> baseSource;
    double driftMagnitude;
    double currentDrift = 0.0;

public:
    DriftDecorator(std::unique_ptr<DataSource> base, double magnitude);

    double getNextValue() override;
};

#endif