#include "sources/DriftDecorator.h"

DriftDecorator::DriftDecorator(std::unique_ptr<DataSource> base, double magnitude) 
    : baseSource(std::move(base)), driftMagnitude(magnitude) {}

SensorDataPoint DriftDecorator::getNextValue() {
    currentDrift += driftMagnitude;
    SensorDataPoint original = baseSource->getNextValue();
    double originalValue = std::get<double>(original.getValue());
    return SensorDataPoint(originalValue + currentDrift);
}