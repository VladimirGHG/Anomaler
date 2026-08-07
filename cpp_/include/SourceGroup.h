#ifndef SOURCE_GROUP_H
#define SOURCE_GROUP_H

#include <array>
#include <string>
#include <variant>
#include <unordered_map>
#include <windows.h>

using FieldValue = std::variant<int, double, std::string, bool>;
using FieldMap = std::unordered_map<std::string, FieldValue>;

/** @brief A class representing a group of data sources.
 * Each source group consists of a name and a list of source types.
 * The class provides functionality to initilalize and manipulate group of sensors simultaneously.
 */

class SourceGroup{
public:

    // Construct a SourceGroup from a list of source type names and attributes {source_name: {{source_type:}, {readport:}, {port:}, {frequency:}, {ml_model:}, {data_mode:}, {serialization:}, {batch_size:}, {verbose:}}.
    SourceGroup(std::unordered_map<std::string, FieldMap> group): group_(std::move(group)) {}

    SourceGroup() = default;

    template<typename... Args>
    void insertUpdate(const std::string& source_name, Args&&... args);

    void remove(const std::string& source_name) {
        group_.erase(source_name);
    }

    void launch();
    void waitAll();
    void terminateAll();

private:
    void setFields(FieldMap&) {}

    template<typename Value, typename... Rest>
    void setFields(FieldMap& entry, const std::string& key, Value&& value, Rest&&... rest) {
        entry[key] = std::forward<Value>(value);
        setFields(entry, std::forward<Rest>(rest)...);
    }

    std::unordered_map<std::string, FieldMap> group_;
    std::vector<PROCESS_INFORMATION> processes_;
};

#endif

