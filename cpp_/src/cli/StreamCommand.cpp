#include "SourceFactory.h"
#include "StreamOptions.h"
#include "ManagerHandshake.h"
#include "DataSenderFactory.h"
#include "PollingLoop.h"

#include <CLI/CLI.hpp>
#include <zmq.hpp>
#include <iostream>

std::string validate_ml_model(const std::string& input) {
    if (input == "RiverHalfSpaceTrees" || input == "SKlearnIsolatedForest" || input == "None") {
        return "";
    }
    if (input.length() >= 4 && input.compare(input.length() - 4, 4, ".pkl") == 0) {
        return "";
    }
    return "Model must be a known type or a path ending in .pkl";
}

CLI::App* setup_stream_command(CLI::App& app, StreamOptions& opts) {

    auto* stream_cmd = app.add_subcommand("stream", "Initialize and start the sensor data stream");
    
    // Data Mode: When creating a stream, the user shall specify the data source.
    // Users can create custom sources by implementing the DataSource interface and adding them to the SourceFactory.
    stream_cmd->add_option("-s,--source", opts.source_type, "The data source to use for the stream")
              ->check(CLI::IsMember(SourceFactory::GetAvailableModes()))
              ->default_val("random");
    
    stream_cmd->add_option("--rp,--readport", opts.readport, "ZeroMQ port for reading the data from the sensor")
              ->capture_default_str();

    stream_cmd->add_option("--sn,--sensor_name", opts.source_name, "Name of the sensor")
              ->capture_default_str();

    // Port: Must be a positive number
    stream_cmd->add_option("-p,--port", opts.port, "ZeroMQ port for the PUSH/PULL bridge")
              ->check(CLI::PositiveNumber)
              ->capture_default_str();

    // Frequency: Must be within realistic hardware bounds (0.05s to 60s)
    stream_cmd->add_option("-f,--freq", opts.frequency, "Polling frequency in seconds")
              ->check(CLI::Range(0.05, 60.0))
              ->capture_default_str();

    // Limit: Allow the user to run controlled experiments
    stream_cmd->add_option("-l,--limit", opts.limit, "Number of points to send before stopping (0 for infinite)")
              ->check(CLI::NonNegativeNumber);

    // Data Mode: Restrict input to specific "Allowed" strings
    stream_cmd->add_option("--dm,--data_mode", opts.data_mode, "The distribution pattern of the data")
              ->check(CLI::IsMember({"default", "noisy", "drift"}))
              ->default_val("default");

    stream_cmd->add_option("--ml,--ml_model", opts.ml_model, "The anomaly detection model to load or to create from scratch")
              ->check(validate_ml_model)
              ->default_val("SKlearnIsolatedForest");
              
    // Batch Size: Allow the user to specify how many points to send in each batch, with a default of 50 and a maximum of 1000 to prevent memory issues
    stream_cmd->add_option("-b,--batch", opts.batch_size, "Number of points to send in each batch (0 for all available)")
              ->check(CLI::NonNegativeNumber)
              ->capture_default_str();
    
    stream_cmd->add_option("--ser,--serialization", opts.serialization, "The serialization protocol to use for sending data (json or flatbuffers)")
              ->check(CLI::IsMember({"json", "flatbuffers"}))
              ->default_val("json");

    stream_cmd->add_option("--g,--group_name", opts.group_name, "Name of the group to which the stream belongs")
              ->capture_default_str();

    stream_cmd->add_flag("-v,--verbose", opts.verbose, "Enable detailed logging for the stream command");

    return stream_cmd;
}

int run_stream(const StreamOptions& opts) {
    if (opts.verbose) {
        std::cout << "[INFO] Initializing Stream on Port: " << opts.port << std::endl;
        std::cout << "[INFO] Pattern: " << opts.source_type << " | Freq: " << opts.frequency << "s" << std::endl;
    }
 
    zmq::context_t context(1);
 
    if (!perform_manager_handshake(context, opts)) {
        std::cerr << "[ERROR] Failed to receive acknowledgment from manager. Exiting." << std::endl;
        return 1;
    }
 
    DataSender data_sender = build_data_sender(opts);
    auto source = SourceFactory::create(opts.source_type, opts.data_mode, opts.readport, opts.source_name);
 
    return run_polling_loop(data_sender, *source, opts);
}