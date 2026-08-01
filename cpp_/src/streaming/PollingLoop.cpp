#include "PollingLoop.h"
#include <atomic>
#include <csignal>
#include <chrono>
#include <thread>
#include <ctime>
#include <iostream>

namespace {

std::atomic<bool> g_shutdown_requested{false};

void handle_shutdown_signal(int) {
    g_shutdown_requested.store(true);
}

void flush_remaining_points(DataSender& sender) {
    if (!sender.stream.dataPoints.empty()) {
        sender.sendBatch(static_cast<int>(sender.stream.dataPoints.size()), true);
    }
}

}

int run_polling_loop(DataSender& sender, DataSource& source, const StreamOptions& opts) {
    std::signal(SIGINT, handle_shutdown_signal);
    std::signal(SIGTERM, handle_shutdown_signal);

    std::cout << "[INFO] Data Stream Started. Press Ctrl+C to stop." << std::endl;

    bool shutting_down = false;
    const auto stream_start = std::chrono::steady_clock::now();
    long long tick_count = 0;
    long long points_sent = 0;

    while (!shutting_down && !g_shutdown_requested.load()) {
        SensorDataPoint dp = source.getNextValue();
        sender.stream.addDataPoint(dp);

        if (opts.verbose) {
            std::cout << "[INFO] Added Data Point: " << dp.getValue() << " at " << dp.getTimestamp() << std::endl;
        }

        if (static_cast<int>(sender.stream.dataPoints.size()) >= opts.batch_size) {
            bool sendOk = sender.sendBatch(opts.batch_size, true);
            
            if (!sendOk) {
                std::cout << "[ERROR] Failed to send batch. Waiting..." << std::endl;
                sender.stream.exportToJsonFile("./unseen_data/unsent_backup_" + std::to_string(std::time(nullptr)) + ".json");
                shutting_down = true;
                continue;
            }

            std::cout << "[INFO] Sent Batch of " << opts.batch_size << " points." << std::endl;
            points_sent += opts.batch_size;
        }

        if (opts.limit > 0 && points_sent >= opts.limit) {
            break;
        }

        tick_count++;
        auto next_deadline = stream_start + std::chrono::duration_cast<std::chrono::steady_clock::duration>(
            std::chrono::duration<double>(opts.frequency * tick_count));
            std::this_thread::sleep_until(next_deadline);
    }

    if (g_shutdown_requested.load()) {
        std::cout << "[INFO] Shutdown signal received, flushing remaining points..." << std::endl;
        flush_remaining_points(sender);
    }

    return 0;
}