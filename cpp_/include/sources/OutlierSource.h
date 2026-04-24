#ifndef OUTLIERSOURCE_H
#define OUTLIERSOURCE_H

#include "DataSource.h"
#include "DataPoint.h"
#include <random>

/** @brief A concrete implementation of DataSource that generates outlier values.
 * This class simulates sensor readings that are significantly different from normal values, useful for testing anomaly detection.
 */
class OutlierSource : public DataSource {
public:    OutlierSource();
    SensorDataPoint getNextValue() override;
};

#endif