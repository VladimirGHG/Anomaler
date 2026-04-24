#include "sources/RandomSource.h"
#include "DataPoint.h"
#include <iostream>

RandomSource::RandomSource() : 
    gen(std::random_device{}()), 
    dist(20.0, 2.0) {}

SensorDataPoint RandomSource::getNextValue() {
    double value = dist(gen);

    static std::uniform_int_distribution<int> anomaly_dist(0.0, 100.0);
    double anomaly_chance = anomaly_dist(gen);

    if (anomaly_chance < 1.0) { // 1% chance to generate an anomaly
        lastWasAnomaly = true;
        double anomaly_shift = (anomaly_chance < 0.5) ? -20.0 : 20.0; // Shift value up or down by 20
        return SensorDataPoint(value + anomaly_shift); // Simulate an anomaly
    }
    lastWasAnomaly = false;
    return SensorDataPoint(value);
}