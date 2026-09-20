# Anomaler

## Overview
Anomaler is a C++/Python system for streaming structured data to anomaly detection models and catching those anomalies. It supports both training and real-time evaluation, enabling efficient end-to-end anomaly detection across arbitrary data types. The system is designed to be modular, flexible, and compatible with ML pipelines.

## Prerequisites
To build and run Anomaler, ensure the following dependencies are installed:

### System and Build Tools:
* **C++17/20** Compiler: Modern Clang or GCC.
* **CMake** (>=3.15) and **Make**, for build orchestration.

### C++ Dependencies (vcpkg)
* **ZeroMQ** (cppzmq): For high-throughput, asynchronous data transmission.
* **CLI11**: For robust command-line parsing.
* **nlohmann_json**: For JSON serialization between C++ and Python.

### Clone the Repo
    git clone https://github.com/VladimirGHG/Anomaler.git

### Python
* Download the required libraries mentioned in *requirements.txt*, using:
    ```
    pip install -r requirements.txt
    ```

## Setting Up C++
* Anomaler uses [vcpkg](https://github.com/microsoft/vcpkg) to manage C++ dependencies. Install by running:
    ```
  vcpkg\vcpkg install zeromq nlohmann-json cppzmq cserialport cli11 yaml-cpp
    ```
  
For MACOS and Windows, after installing the required libraries, the remaining setup part is a bit different. Please find the steps for both of those mentioned below.
### MACOS
* After installing all the needed packages, build the C++ Manager and run CMake while pointing to your vcpkg toolchain file:\
  ```
  make
  ```

### Windows
* After installing all the needed packages, build the C++ Manager, and run the pre-written build.bat:\
  ```
  cpp_\build.bat
  ```

### Generating the Flatbuffers' script for Python side
* Finally, basd on the data structures defined in th .fbs file, the Python script for those should be generated. Run from the cpp_ folder:\
  ```
  ./vcpkg/installed/arm64-osx/tools/flatbuffers/flatc \
    --python \
    --gen-object-api \
    -o ../py_analytics/serialization/generated/python \
    ../py_analytics/serialization/schemas/telemetry.fbs
  ```

## Features (Some are yet prospective)
**End-to-end support**: Anomaler supports the end-to-end cycle of developing an anomaly detection model, from data generation and transformation to model training and evaluation.

**Hybrid ML support**: Native integration for online learning models (River's HalfSpaceTrees) and batch-based learning models (Scikit-learn's Isolation Forest).

**Distributed Architecture**: Decoupled C++ data ingestion and Python analytics via ZeroMQ for high concurrency and scalability.

**Full Control Through the CLI**: Easily control the entire process of setting up data streams, data sources, and machine models via CLI.

**Hardware Abstraction Layer**: Easy sensor connection to the system using prebuilt abstract classes and add settings specifically to that sensor.

**Virtual Sensor Creation Support**: Sensor replication, allowing to reliably replace the broken sensors for a limited time, until it gets replaced.
## Structure

### Note
*Since in the system the basic River and scikit-learn models are wrapped by the system's classes, to integrate those with the cpp part, those classes are going to be referred to as Strategies throughout this documentation.*

Anomaler consists of two three parts: 
* The *config* part, used to define data streams and their groups.
  * *group_config.yaml* is the main configurational file, where the user can define groups and streams. The YAML file will be parsed and all the instances mentioned in it will be initialized.

* The *py_analytics* part, where the ML models and everything connected with them are defined
  * *models_saved/* is the folder where the snapshots are saved by default.
  
  * *main.py* is what needs to be run to connect the Python side to C++. Stream configs, such as communication ports, are sent to the Python manager from C++ via a ZMQ socket.
  * *anomalytrig.py* is a small script used to inject anomalies into the data stream for strategy-testing purposes.
  * *config/* contains all the config dataclasses for the Python-side abstractions.
      * *group_config.py* is a dataclass, containing all the configs of a specific **stream group**.
      * *stream_config.py* is a dataclass, containing all the configs of a specific **stream**.
      * *worker_context.py* is a dataclass, containing all the configs for initializing the worker (Currently it has three attributes: **group_id, group_runtime (GroupRuntime instance), stream_config (StreamConfig instance)**)
  * *manager/* contains all the Python-side managers.
      * *group_runtime.py* organizes the work that should be carried out for a stream group. Its crucial attribute is the *GroupConfig* instance. When a worker is initialized for a data stream within the group, it registers the worker's context. GroupRuntime is also the middle point for creating the Virtual Sensor based on the target sensor of a group. It organizes the data batches to perform PCA and start the creation of the Virtual Sensor.
      * *manager.py* contains the starting manager that runs the *RuntimeManager* and shuts it down.
      * *runtime_manager.py* contains the RuntimeManager class, which has an active ZMQ Poller for receiving events and autodefines what should be done based on the event socket. It is responsible for registering/initializing streams with their ZMQWorkers and registering groups. It also receives the data batches sent by the ZMQWorkers, serialized via FlatBuffers, and passes them to GroupRuntime instances, so those can carry out PCA for Virtual Sensor creation.
  * *models/* is the folder containing all the ML strategies (Amodels).
      * *base.py* contains the abstract class that all the strategies (Amodels) of the system must inherit from.
      * *river_strategy.py*  is where the online-based *HalfSpaceTrees*'s wrapper *RiverStrategy* class is located.
      * *sklearn_strategies/* contains scikit-learn-based strategies. 
          * *isolationforest_strategy.py* contains *IsolationForestStrategy* wrapper class for the scikit-learn's *IsolationForest*.
  * *models_saved/* contains the saved models in subfolders with strategy names. (The folder and its subfolders are **autogenerated** by the system)
  * *serialization/* contains the *schemas/* folder where the .fbs file is defined for defining the data structures for FlatBuffers. In *generated/python/*, the FlatBuffers-generated data structures, based on the .fbs file, are contained.
  * *transport/* is where Python-side data transportation means are defined.
      * *discovery.py* contains the discovery socket creation function. The discovery socket is the socket through which new stream configuration and initialization events are sent to the RuntimeManager.
      * *ZmqTransport/* folder contains ZMQ transportation means via FlatBuffers.
          * *FlatBuffersSender.py* contains the FlatBuffersSender class, used to easily send data batches over a ZMQ socket with FlatBuffers serialization. It has send() and serialize() methods.
          * *FlatBuffersReceiver.py* contains the FlatBuffersReceiver class, used to easily receive data batches. It has receive() and deserialize() methods.
  * *virtual_sensors/* contains the base virtual sensor class script and pre-requisite procedures' scripts, such as PCA. (UNFINISHED)
  * *workers/* is the folder containing everything connected with workers.
      * *worker.py* The worker is initialized by the runtime_manager to wait for packages from the C++ side, initialize strategies, train the model, process the data from C++ to highlight anomalies, perform model snapshot saving/loading, report, log, and provide basic model precision metrics.
      * *process.py* is the entry point for creating the ZMQWorkers and running it. runtime_manager calls the *run_model_worker_process* function to initialize and run the worker.

* The *cpp_* part is responsible for data generation, data transformation, and data transfer to the Python side.
  * *builds/* is the folder where the builds of the system are stored.
  * *include/* stores the header files with initial definitions of the classes.
  * *src/* includes the main source C++ code.
  
    * *sources/* folder includes classes for the data sources. These classes interface with a hardware sensor, gathering the data from it,       and returning it in the form of a *SensorDataPoint* object. All of them inherit from the *DataSource* class that defines all the            required methods for the source to work with the rest of the system. Users can create their own source classes to connect their             sensors to the system, but it is highly recommended to design them so that it inherits from the *DataSource* class and define all the       required methods.
    
      * *DriftDecorator.cpp* is a source class decorator (wrapper) that is used to add a drift coefficient to test the Amodels' behavior           during scenarios when the sensors wear out.
      * *OutlierSource.cpp* generates big (>100) random values. Can be used as a data source for some tests.
      * *RandomSource.cpp* generates random values and, with a chance of 1%, injects an outlier (anomaly).
      * *SerialSensorSource.cpp* is a real data source that receives and formats the numerical data from sensors.
  
    * *DataPoints.cpp* is an abstraction for sending data from C++ to Python more conveniently. With each new data point from the sensor, a        new *DataPoint* object is created. It has three attributes: value, isAnomaly, and timestamp.
      * value: can be any object from *DataValue* defined in *DataTypes.h*.
      * isAnomaly: Used for testing purposes, for instance, when a person purposefully injects an anomalous value to check the                     precision of the ML model.
      * timestamp: Might be helpful again for testing/logging, and if the system is used in real-world anomaly detection tasks, to identify        when an anomaly happened.
    * *DataSender.cpp* is used for sending batches of data to the Python side, to the Amodels.
    * *DataStream.cpp* is used as a connector between *DataSource* and *DataSender*, prepares the data for sending, logs it, and removes it        from the stream.
    * *main.cpp* is the build file where the possible CLI commands are defined.
    * *SourceFactory.cpp* is the control unit that is used to initialize the work of the data source, based on the command from the CLI.
  * *unseen_data/* contains csv files with sensor-generated data points that did not reach the Python side due to any issue. 
  * *vcpkg* is a package manager for C++ packages. Needed for easy use of the system.
  * *Makefile* is used to build the project on MacOS, by running the `make` command in the terminal.
  * *build.bat* is used to build the project on Windows, by running `build` command in the terminal.


## Starting Anomaler
After having everything set up, you can easily run the clients on the C++ and Python sides using the below-mentioned commands.

### Run the C++ side
#### To initialize a single stream: mentioning only the port, the frequency, the data source, the data transmission mechanism, and other features of the initialized data stream, is set to their default values. (Mention any port besides 5555, since it is used by default for the communication manager between C++ and Python)
    cpp_/builds/main stream --port XXXX
#### To run instances mentioned in the YAML config file
    cpp_/builds/main group
### Run the Python side
#### There are no configuration specifications on Python's side. Everything needed is sent to Python from C++ by the manager when a data stream is initialized on the C++ side.
    python -m py_analytics.main

