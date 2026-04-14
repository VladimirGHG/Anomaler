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
    std::string model;
    std::string data_mode;

    // Data Mode: When creating a stream, the user shall specify the data source.
    // Users can create custom sources by implementing the DataSource interface and adding them to the SourceFactory.
    stream_cmd->add_option("-s,--source", model, "The data source to use for the stream")
              ->check(CLI::IsMember(SourceFactory::GetAvailableModes()))
              ->default_val("random");

    // Port: Must be a positive number
    stream_cmd->add_option("-p,--port", port, "ZeroMQ port for the PUSH/PULL bridge")
              ->check(CLI::PositiveNumber)
              ->capture_default_str();

    // Frequency: Must be within realistic hardware bounds (0.1s to 60s)
    stream_cmd->add_option("-f,--freq", frequency, "Polling frequency in seconds")
              ->check(CLI::Range(0.1, 60.0))
              ->capture_default_str();

    // Limit: Allow the user to run controlled experiments
    stream_cmd->add_option("-l,--limit", limit, "Number of points to send before stopping (0 for infinite)")
              ->check(CLI::NonNegativeNumber);

    // Data Mode: Restrict input to specific "Allowed" strings
    stream_cmd->add_option("-m,--mode", data_mode, "The distribution pattern of the data")
              ->check(CLI::IsMember({"normal", "noisy", "drift"}))
              ->default_val("normal");

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
            std::cout << "[INFO] Pattern: " << model << " | Freq: " << frequency << "s" << std::endl;
        }

        // Initialize ZeroMQ Context
        zmq::context_t context(1);

        // Handshake with Manager
        zmq::socket_t announcer(context, zmq::socket_type::req);
        announcer.connect("tcp://localhost:5555");

        nlohmann::json registration = {
            {"action", "start"},
            {"port", port},      // from CLI11 option
            {"model", model},    // from CLI11 option
            {"mode", data_mode}  // from CLI11 option
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

        // Initialize the data source from the factory
        auto source = SourceFactory::create(model, data_mode);
        std::cout << "[INFO] Starting data stream..." << std::endl;
        while(true){
            DataValue current_val = source->getNextValue(); 

            // Create a stable point and add it to the stream
            data_sender.stream.addDataPoint(SensorDataPoint(current_val));

            // Send if batch is ready
            if (data_sender.stream.dataPoints.size() >= 50) {
                res = data_sender.send(50);
                // data_sender.stream.exportToJsonFile("test.json"); // For debugging purposes, export the batch to a JSON file
                // data_sender.stream.clear(); // to be implemented: clear the stream after sending to avoid memory issues
                if (!res) {
                    std::cout << "[ERROR] Failed to send batch. Waiting..." << std::endl;
                }
            }

            std::this_thread::sleep_for(std::chrono::duration<double>(frequency));
        }
        
        std::cout << ">>> Data Stream Started. Press Ctrl+C to stop." << std::endl;
    } else {
        std::cout << app.help() << std::endl;
    }

    return 0;
}