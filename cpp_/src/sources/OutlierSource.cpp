#include "sources/OutlierSource.h"

OutlierSource::OutlierSource() = default;

double OutlierSource::getNextValue() {
    return 100.0 + (rand() % 10);
}