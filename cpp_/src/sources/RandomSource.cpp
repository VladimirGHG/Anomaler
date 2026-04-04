#include "sources/RandomSource.h"

RandomSource::RandomSource() : 
    gen(std::random_device{}()), 
    dist(20.0, 2.0) {}

double RandomSource::getNextValue() {
    return dist(gen);
}