#include <CLI/CLI.hpp>

#include "SourceFactory.h"
#include "StreamOptions.h"

void setup_stream_command(CLI::App& app, StreamOptions& opts) {

    auto* stream_cmd = app.add_subcommand("stream", "Initialize and start the sensor data stream");

    // Data Mode: When creating a stream, the user shall specify the data source.
    // Users can create custom sources by implementing the DataSource interface and adding them to the SourceFactory.
    stream_cmd->add_option("-s,--source", opts.source_type, "The data source to use for the stream")
              ->check(CLI::IsMember(SourceFactory::GetAvailableModes()))
              ->default_val("random");
    
    stream_cmd->add_option("--rp,--readport", opts.readport, "ZeroMQ port for reading the data from the sensor")
              ->capture_default_str();

    stream_cmd->add_option("--sn,--sensorname", opts.sensorname, "Name of the sensor")
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
              ->check(CLI::IsMember({"normal", "noisy", "drift"}))
              ->default_val("normal");

    stream_cmd->add_option("--ml,--ml_model", opts.ml_model, "The anomaly detection model to load or to create from scratch")
              ->check(validate_ml_model)
              ->default_val("SKlearnIsolatedForest");
              
    // Batch Size: Allow the user to specify how many points to send in each batch, with a default of 50 and a maximum of 1000 to prevent memory issues
    stream_cmd->add_option("-b,--batch", opts.batch_size, "Number of points to send in each batch (0 for all available)")
              ->check(CLI::NonNegativeNumber)
              ->capture_default_str();
    
    stream_cmd->add_option("--ser,--serialization", opts.serialization, "Number of points to send in each batch (0 for all available)")
              ->check(CLI::IsMember({"json", "flatbuffers"}))
              ->default_val("json");

    stream_cmd->add_flag("-v,--verbose", opts.verbose, "Enable detailed logging for the stream command");
}

std::string validate_ml_model(const std::string& input) {
    if (input == "RiverHalfSpaceTrees" || input == "SKlearnIsolatedForest") return "";
    if (input.size() >= 4 && input.compare(input.size() - 4, 4, ".pkl") == 0) return "";
    return "Model must be a known type or a path ending in .pkl";
}