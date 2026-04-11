#define CLI11_HAS_FILESYSTEM 0
#include <CLI/CLI.hpp>
#include <iostream>
#include <chrono>
#include <thread>
#include <zmq.hpp>
#include <nlohmann/json.hpp>
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
        zmq::socket_t data_sender(context, zmq::socket_type::push);
        data_sender.connect("tcp://localhost:" + std::to_string(port));
        
        // Initialize the data source from the factory
        auto source = SourceFactory::create(model, data_mode);
        int points_sent = 0;

        while(true){
            double current_val = source->getNextValue();
            
            // Prepare JSON packet for the analytics engine
            nlohmann::json packet;
            packet["datapoints"] = {{ {"value", current_val}, {"timestamp", points_sent} }};

            data_sender.send(zmq::buffer(packet.dump()), zmq::send_flags::none);

            if (verbose) {
                std::cout << "[DEBUG] Sent data point: " << current_val << " to port " << port << std::endl;
            }
            if (limit > 0 && points_sent >= limit) {
                std::cout << "[INFO] Reached limit of " << limit << " points. Stopping stream." << std::endl;
                break;
            }
            points_sent++;
            std::this_thread::sleep_for(std::chrono::duration<double>(frequency));
            printf("\r[INFO] Points Sent: %d", points_sent);
            fflush(stdout);
        }
        
        std::cout << ">>> Data Stream Started. Press Ctrl+C to stop." << std::endl;
    } else {
        // If no subcommand is provided, show the help menu by default
        std::cout << app.help() << std::endl;
    }

    return 0;
}