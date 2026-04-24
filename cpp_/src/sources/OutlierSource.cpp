#include "sources/OutlierSource.h"

OutlierSource::OutlierSource() = default;

SensorDataPoint OutlierSource::getNextValue() {
    return SensorDataPoint(100.0 + (rand() % 10));
}