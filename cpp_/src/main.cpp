#define CLI11_HAS_FILESYSTEM 0
#include <CLI/CLI.hpp>
#include <iostream>
#include <chrono>
#include <thread>
#include <zmq.hpp>
#include <nlohmann/json.hpp>
#include "SourceFactory.h"
#include "DataSender.h"

int main(int argc, char** argv) {
    // Main Application
    CLI::App app{"Anomaler: High-Performance Data Producer for ML Pipelines"};
    
    // Global settings that can be used across all commands
    bool verbose = false;
    app.add_flag("-v,--verbose", verbose, "Enable detailed console logging");

    // "Stream" Subcommand
    // This creates a dedicated mode: ./main stream [options]
    auto* stream_cmd = app.add_subcommand("stream", "Initialize and start the sensor data stream");

    // Define Scoped Options (Variables only used for streaming)
    int port = 5555;
    double frequency = 0.05;
    int limit = 0;
    int batch_size = 50;
    std::string source_type;
    std::string data_mode;
    std::string ml_model;
    std::string readport;
    std::string sensorname;

    // Data Mode: When creating a stream, the user shall specify the data source.
    // Users can create custom sources by implementing the DataSource interface and adding them to the SourceFactory.
    stream_cmd->add_option("-s,--source", source_type, "The data source to use for the stream")
              ->check(CLI::IsMember(SourceFactory::GetAvailableModes()))
              ->default_val("random");
    
    stream_cmd->add_option("--rp,--readport", readport, "ZeroMQ port for reading the data from the sensor")
              ->capture_default_str();

    stream_cmd->add_option("--sn,--sensorname", sensorname, "Name of the sensor")
              ->capture_default_str();

    // Port: Must be a positive number
    stream_cmd->add_option("-p,--port", port, "ZeroMQ port for the PUSH/PULL bridge")
              ->check(CLI::PositiveNumber)
              ->capture_default_str();

    // Frequency: Must be within realistic hardware bounds (0.05s to 60s)
    stream_cmd->add_option("-f,--freq", frequency, "Polling frequency in seconds")
              ->check(CLI::Range(0.05, 60.0))
              ->capture_default_str();

    // Limit: Allow the user to run controlled experiments
    stream_cmd->add_option("-l,--limit", limit, "Number of points to send before stopping (0 for infinite)")
              ->check(CLI::NonNegativeNumber);

    // Data Mode: Restrict input to specific "Allowed" strings
    stream_cmd->add_option("--dm,--data_mode", data_mode, "The distribution pattern of the data")
              ->check(CLI::IsMember({"normal", "noisy", "drift"}))
              ->default_val("normal");

    stream_cmd->add_option("--ml,--ml_model", ml_model, "The anomaly detection model to load or to create from scratch")
              ->check([](const std::string &input) {
                // Check if it's a known keyword
                if (input == "RiverHalfSpaceTrees" || input == "SKlearnIsolatedForest") {
                    return std::string(); // Empty string means success
                }
                
                // Check if it ends in .pkl
                if (input.length() >= 4 && input.compare(input.length() - 4, 4, ".pkl") == 0) {
                    return std::string(); // Success
                }

                // Return error message if neither
                return std::string("Model must be a known type or a path ending in .pkl");
              })
              ->default_val("SKlearnIsolatedForest");
              
    // Batch Size: Allow the user to specify how many points to send in each batch, with a default of 50 and a maximum of 1000 to prevent memory issues
    stream_cmd->add_option("-b,--batch", batch_size, "Number of points to send in each batch (0 for all available)")
              ->check(CLI::NonNegativeNumber)
              ->capture_default_str();

    stream_cmd->add_flag("-v,--verbose", verbose, "Enable detailed logging for the stream command");

    // The Parsing "Handshake"
    try {
        app.parse(argc, argv);
    } catch (const CLI::ParseError &e) {
        return app.exit(e);
    }

    // Execution Logic (The "Dispatcher")
    if (app.got_subcommand(stream_cmd)) {
        if (verbose) {
            std::cout << "[INFO] Initializing Stream on Port: " << port << std::endl;
            std::cout << "[INFO] Pattern: " << source_type << " | Freq: " << frequency << "s" << std::endl;
        }

        // Initialize ZeroMQ Context
        zmq::context_t context(1);

        // Handshake with Manager
        zmq::socket_t announcer(context, zmq::socket_type::req);
        announcer.connect("tcp://localhost:5555");

        nlohmann::json registration = {
            {"action", "start"},
            {"port", port},         // from CLI11 option
            {"model", source_type}, // from CLI11 option
            {"mode", data_mode},    // from CLI11 option
            {"ml_model", ml_model}  // from CLI11 option
        };

        announcer.send(zmq::buffer(registration.dump()), zmq::send_flags::none);

        // Wait for Python to reply with acknowledgment before starting the stream
        zmq::message_t reply;
        auto res = announcer.recv(reply, zmq::recv_flags::none); 

        // If we don't get a reply, it means the manager is not running or there's a connection issue
        if (!res) {
            std::cerr << "[ERROR] Failed to receive acknowledgment from manager. Exiting." << std::endl;
            return 1;
        }
        // Now start the actual data stream on the dynamic port
        DataSender data_sender("tcp://127.0.0.1:" + std::to_string(port));

        // Set socket options for reliability and performance, so that no memory leaks occur, when the receiver is offline.
        data_sender.socket.set(zmq::sockopt::sndhwm, 10);
        data_sender.socket.set(zmq::sockopt::immediate, 0);
        data_sender.socket.set(zmq::sockopt::linger, 0);

        // Initialize the data source from which data points will be generated
        auto source = SourceFactory::create(source_type, data_mode, readport, sensorname);

        std::cout << "[INFO] Starting data stream..." << std::endl;
        while(true){
            SensorDataPoint dp = source->getNextValue(); 
            // bool isAnomaly = source->wasAnomaly();
            // Create a stable point and add it to the stream
            data_sender.stream.addDataPoint(dp);

            // Send if batch is ready
            if (data_sender.stream.dataPoints.size() >= batch_size) {
                res = data_sender.send(batch_size, true); // Send the batch and clear after sending
                // data_sender.stream.exportToJsonFile("test.json"); // For debugging purposes, export the batch to a JSON file
                if (!res) {
                    std::cout << "[ERROR] Failed to send batch. Waiting..." << std::endl;
                }
                data_sender.stream.clear(); // Clear the stream after sending to avoid memory issues
            }

            std::this_thread::sleep_for(std::chrono::duration<double>(frequency));
        }
        
        std::cout << ">>> Data Stream Started. Press Ctrl+C to stop." << std::endl;
    } else {
        std::cout << app.help() << std::endl;
    }

    return 0;
}