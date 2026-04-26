# Anomaler

## Overview
Anomaler is a C++ system for streaming structured data to an anomaly detection model. It supports both training and real-time evaluation, enabling efficient end-to-end anomaly detection across arbitrary data types. The system is designed to be modular, flexible, and compatible with ML pipelines.

## Features
**End-to-end support**: Anomaler supports the end-to-end cycle of developing an anomaly detection model, from data generation and transformation to model training and evaluation.

**Hybrid ML support**: Native integration for online learning models (River's HalfSpaceTrees) and a batch-based learning models (Sklearn's Isolated Forest).

**Distributed Architecture**: Decoupled C++ data ingestion and Python analytics via ZeroMQ for high concurrency and scalability.

**Full Control Through the CLI**: Easily control the entire process of setting up data streams, data sources, and machine models via CLI.

**Hardware Abstraction Layer**: You can connect nearly any sensor to the system using prebuilt abstract classes and add settings specifically to that sensor.

## Structure

### Note
*Since in the system the basic River and SKlearn models are wrapped by the system's classes, to integrate those with the cpp part, those classes are going to be referred to as 'Amodels' throughout this documentation.*

Anomaler consists of two main parts: 
* The *py_analytics* part, where the ML models and everything connected with them are defined
  * *models/* is the folder where the snapshots are saved by default.

  * *analytics.py* is what needs to be run to connect the Python side to Cpp. Starts the manager tracking a specific port for messages from     the CLI to start a ZMQWorker with specific settings.
  * *anomalytrig.py* a small script used to inject anomalies into the data stream, for Amodel-testing purposes.
  * *amodels.py*  is where the two types of Amodels' source codes are: *RiverStrategy*, and *IsolatedForestStrategy* classes.
  * *worker.py* is the worker that is initialized by the manager to wait for packages from the cpp side and perform model snapshots' saving     and loading, as well as report, log, and provide basic model precision metrics.
    
* The *cpp_* part, which is responsible for data generation, data transformation, and data transfer to the Python side.
  * *builds/* is the folder where the builds of the system are stored.
  * *include/* stores the header files with initial definitions of the classes.
  * *src/* includes the main source C++ code.
  
    * *sources/* folder includes classes for the data sources. These classes interface with a hardware sensor, gathering the data from it,       and returning it in the form of a *SensorDataPoint* object. All of them inherit from the *DataSource* class that defines all the            required methods for the source to work with the rest of the system. Users can create their own source classes to connect their             sensors to the system, but it is highly recommended to design them so that it inherits from the *DataSource* class and define all the       required methods.
    
      * *DriftDecorator.cpp* is a source class decorator (wrapper) that is used to add a drift coefficient to test the Amodels' behavior           during the scenarios when the sensors wear out.
      * *OutlierSource.cpp* generates big (>100) random values. Can be used as a data source for some tests.
      * *RandomSource.cpp* generates random values and, with a chance of 1%, injects an outlier (anomaly).
      * *SerialSensorSource.cpp* is a real data source that receives and formats the numerical data from sensors.
  
    * *DataPoints.cpp* is an abstraction for sending data from C++ to Python more conveniently. With each new data point from the sensor, a        new *DataPoint* object is created. It has three attributes: value, isAnomaly, timestamp.
      * value: can be any object from *DataValue* defined in *DataTypes.h*.
      * isAnomaly: Used for testing purposes, for instance, when a person purposefully injects an anomalous value to check the                     precision of the ML model.
      * timestamp: Might be helpful again for testing/logging, and if the system is used in real-world anomaly detection tasks, to identify        when an anomaly happened.
    * *DataSender.cpp* is used for sending batches of data to the Python side, to the Amodels.
    * *DataStream.cpp* is used as a connector between *DataSource* and *DataSender*, prepares the data for sending, logs it, and removes it        from the stream.
    * *main.cpp* is the build file where the possible CLI commands are defined.
    * *SourceFactory.cpp* is the control unit that is used to initialize the work of the data source, based on the command from the CLI.
  * *vcpkg* is a package manager for C++ packages. Needed for easy use of the system.
  * *Makefile* is used for easily building the build by running just the make command in the terminal.
    
## Prerequisites
To build and run Anomaler, ensure the following dependencies are installed:

### System and Build Tools:
* **C++17/20** Compiler: Modern Clang or GCC.
* **CMake** (>=3.15) and **Makefile**, for build orchestration.

### C++ Dependancies (vcpkg)
* **ZeroMQ** (cppzmq): High-throughput data transmission.
* **CLI11**: Command line parsing.
* **nlohmann_json**: JSON serialization.

### Python
* Download the required libraries mentioned in *requirements.txt*, using: `pip install -r requirements.txt`
  
