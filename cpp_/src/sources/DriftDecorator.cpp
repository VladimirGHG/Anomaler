#include "sources/DriftDecorator.h"

DriftDecorator::DriftDecorator(std::unique_ptr<DataSource> base, double magnitude) 
    : baseSource(std::move(base)), driftMagnitude(magnitude) {}

double DriftDecorator::getNextValue() {
    currentDrift += driftMagnitude;
    return baseSource->getNextValue() + currentDrift;  // Adds drift to the base value
}   