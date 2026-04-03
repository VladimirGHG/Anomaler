#include <iostream>
#include <chrono>
#include <thread>
#include "DataPoint.h"
#include "DataStream.h"
#include "DataSender.h"

int main() {
    SensorDataPoint data1(std::vector<std::string>{"hi", "hello", "hey"});
    SensorDataPoint data2(std::vector<double>{12.3, 13.0, 12.9});
    SensorDataPoint data3(42);

    DataStream dataStream;
    dataStream.addDataPoint(data1);
    dataStream.addDataPoint(data2);
    dataStream.addDataPoint(data3);

    while (true){
        DataSender sender;
        sender.send(dataStream);
        std::this_thread::sleep_for(std::chrono::seconds(10));
    }
    // dataStream.exportToJsonFile("test.json");
    // dataStream.exportToCsvFile("test.csv");
    // std::cout << dataStream.getDataPoint() << "\n" << dataStream.getDataPoint() << std::endl;

    return 0;
}