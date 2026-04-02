#include <iostream>
#include "DataPoint.h"
#include "DataStream.h"

int main() {
    SensorDataPoint data1(std::vector<std::string>{"hi", "hello", "hey"});
    SensorDataPoint data2(std::vector<double>{12.3, 13.0, 12.9});
    SensorDataPoint data3(42);

    DataStream dataStream;
    dataStream.addDataPoint(data1);
    dataStream.addDataPoint(data2);
    dataStream.addDataPoint(data3);

    std::cout << dataStream.getDataPoint() << "\n" << dataStream.getDataPoint() << std::endl;

    return 0;
}