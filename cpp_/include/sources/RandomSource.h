#ifndef RANDOMSOURCE_H
#define RANDOMSOURCE_H

#include "DataSource.h"
#include <random>

/** @brief A concrete implementation of DataSource that generates random values following a normal distribution.
 * This class simulates real sensor readings with some noise.
 */
class RandomSource : public DataSource {
private:
    std::mt19937 gen;
    std::normal_distribution<double> dist;
protected:
    bool lastWasAnomaly = false;
public:
    RandomSource();
    SensorDataPoint getNextValue() override;
    bool wasAnomaly() const override { return lastWasAnomaly; };
};

#endif