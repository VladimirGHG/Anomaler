#ifndef SOURCE_GROUP_H
#define SOURCE_GROUP_H

#include <array>
#include <string>
#include <unordered_map>
#include <windows.h>

struct ArrayStringHash {
    std::size_t operator()(const std::array<std::string, 2>& a) const noexcept {
        std::size_t h1 = std::hash<std::string>{}(a[0]);
        std::size_t h2 = std::hash<std::string>{}(a[1]);
        return h1 ^ (h2 + 0x9e3779b9 + (h1 << 6) + (h1 >> 2)); // boost-style combine
    }
};

/** @brief A class representing a group of data sources.
 * Each source group consists of a name and a list of source types.
 * The class provides functionality to initilalize and manipulate group of sensors simultaneously.
 */

class SourceGroup{
public:

    // Construct a SourceGroup from a list of source type names and frequencies <name: [port, frequency]>.
    SourceGroup(std::unordered_map<std::array<std::string, 2>, std::pair<int, double>, ArrayStringHash> group): group_(group) {}

    // Default constructor
    SourceGroup() = default;

    // Add a source name to the group with a specified frequency, or update the frequency if the source type already exists.
    void insertUpdate(const std::string& source_type, const std::string& source_name, double frequency = -1.0, int port = -1) {
        if (frequency != -1.0 && port != -1) {
            group_[{source_type, source_name}] = {port, frequency};
        } else if (frequency != -1.0) {
            group_[{source_type, source_name}].second = frequency;
        } else if (port != -1) {
            group_[{source_type, source_name}].first = port;
        }
    }

    // Remove a source name from the group.
    void remove(const std::string& source_type, const std::string& source_name) {
        group_.erase({source_type, source_name});
    }

    // Launch the work of all sources in the group.
    void launch();
    void waitAll();
    void terminateAll();

private:
    std::unordered_map<std::array<std::string, 2>, std::pair<int, double>, ArrayStringHash> group_;
    std::vector<PROCESS_INFORMATION> processes_;
};

#endif

