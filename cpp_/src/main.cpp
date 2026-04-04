#define CLI11_HAS_FILESYSTEM 0
#include <CLI/CLI.hpp>
#include <iostream>
#include <chrono>
#include <thread>
#include "DataPoint.h"
#include "DataStream.h"
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
    double frequency = 1.0;
    int limit = 0; // 0 means infinite
    std::string data_mode = "random";

    // Data Mode: When creating a stream, the user shall specify the data source.
    // Users can create custom sources by implementing the DataSource interface and adding them to the SourceFactory.
    stream_cmd->add_option("-s,--source", data_mode, "The data source to use for the stream")
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
              ->check(CLI::IsMember({"normal", "noisy", "outlier"}))
              ->default_val("normal");

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
            std::cout << "[INFO] Pattern: " << data_mode << " | Freq: " << frequency << "s" << std::endl;
        }

        int points_sent = 0;

        while(true){
            if (verbose) {
                std::cout << "[DEBUG] Sent data point: " << "YOUR DATA POINT" << std::endl;
            }
            if (limit > 0 && points_sent >= limit) {
                std::cout << "[INFO] Reached limit of " << limit << " points. Stopping stream." << std::endl;
                break;
            }
            points_sent++;
            std::this_thread::sleep_for(std::chrono::duration<double>(frequency));
        }
        
        std::cout << ">>> Data Stream Started. Press Ctrl+C to stop." << std::endl;
    } else {
        // If no subcommand is provided, show the help menu by default
        std::cout << app.help() << std::endl;
    }

    return 0;
}