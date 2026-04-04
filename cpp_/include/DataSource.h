#ifndef DATASOURCE_H
#define DATASOURCE_H

/**
 * @class DataSource
 * @brief Abstract base class for all data generation strategies.
 * * This interface allows the Anomaler system to decouple data production 
 * from network transmission. To add a new sensor, inherit from this class.
 */
class DataSource {
public:
    virtual ~DataSource() = default;
    virtual double getNextValue() = 0;
};

#endif