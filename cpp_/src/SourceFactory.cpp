#include "SourceFactory.h"
#include "sources/RandomSource.h"
#include "sources/OutlierSource.h"

std::unique_ptr<DataSource> SourceFactory::create(const std::string& mode) {
    if (mode == "outlier") {
        return std::make_unique<OutlierSource>();
    }
    // Add more modes here as needed to create different types of data sources, such as "temperature", "pressure", etc.

    return std::make_unique<RandomSource>();
}
