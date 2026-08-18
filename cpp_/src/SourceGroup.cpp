#include "SourceGroup.h"
#include <iostream>
#include <sstream>
#include <zmq.hpp>
namespace {

const std::unordered_map<std::string, std::string> kFieldToFlag = {
    {"port", "-p"},
    {"verbose", "-v"},
    {"group_id", "-g"},
    {"frequency", "-f"},
    {"batch_size", "-b"},
    {"ml_model", "--ml"},
    {"readport", "--rp"},
    {"source_type", "-s"},
    {"data_mode", "--dm"},
    {"source_name", "--sn"},
    {"serialization", "--ser"},
};

std::string valueToString(const FieldValue& value) {
    return std::visit([](auto&& v) -> std::string {
        using T = std::decay_t<decltype(v)>;
        if constexpr (std::is_same_v<T, bool>) {
            return v ? "true" : "false";
        } else if constexpr (std::is_same_v<T, std::string>) {
            return v;
        } else {
            return std::to_string(v);
        }
    }, value);
}

}

template<typename... Args>
void SourceGroup::insertUpdate(const std::string& source_name, Args&&... args) {
    static_assert(sizeof...(Args) % 2 == 0, "Fields must be passed as key-value pairs");

    FieldMap& entry = group_[source_name];
    setFields(entry, std::forward<Args>(args)...);
}

void SourceGroup::launch() {
    for (const auto& [source_name, attributes] : group_) {

        // source_type is always required, since it determines what the source needs.
        auto typeIt = attributes.find("source_type");
        if (typeIt == attributes.end()) {
            std::cerr << "[ERROR] Source '" << source_name << "' has no source_type set, skipping.\n";
            continue;
        }

        std::ostringstream command;
        command << ".\\builds\\main stream";

        // Compose the command from whatever fields are actually present.
        for (const auto& [field, flag] : kFieldToFlag) {
            if (field == "verbose") continue;
            auto it = attributes.find(field);
            if (it == attributes.end()) continue;
            command << " " << flag << " " << valueToString(it->second);
        }
        
        if (auto vIt = attributes.find("verbose"); vIt != attributes.end()) {
            if (const bool* b = std::get_if<bool>(&vIt->second); b && *b) {
                command << " -v";
            }
        }

        std::string cmdStr = command.str();

        STARTUPINFOA si{};
        si.cb = sizeof(si);
        PROCESS_INFORMATION pi{};

        std::vector<char> cmdBuf(cmdStr.begin(), cmdStr.end());
        cmdBuf.push_back('\0');
        
        BOOL ok = CreateProcessA(
            nullptr,
            cmdBuf.data(),
            nullptr, nullptr,
            FALSE,
            CREATE_NEW_CONSOLE,
            nullptr,
            nullptr,
            &si, &pi
        );

        if (!ok) {
            std::cerr << "[ERROR] Failed to launch source: " << source_name
                        << " (error " << GetLastError() << ") with command: "
                        << cmdStr << std::endl;
            continue;
        }

        std::cout << "[INFO] Launched source '" << source_name << "' as PID " << pi.dwProcessId << std::endl;

        processes_.push_back(pi);
        CloseHandle(pi.hThread);
    }
}

void SourceGroup::waitAll() {
    std::vector<HANDLE> handles;
    for (auto& pi : processes_) handles.push_back(pi.hProcess);

    if (handles.empty()) return;

    WaitForMultipleObjects(static_cast<DWORD>(handles.size()), handles.data(), TRUE, INFINITE);

    for (auto& pi : processes_) {
        DWORD exitCode = 0;
        GetExitCodeProcess(pi.hProcess, &exitCode);
        std::cout << "[INFO] PID " << pi.dwProcessId << " exited with code " << exitCode << std::endl;
        CloseHandle(pi.hProcess);
    }
    processes_.clear();
}

void SourceGroup::terminateAll() {
    for (auto& pi : processes_) {
        TerminateProcess(pi.hProcess, 0);
        CloseHandle(pi.hProcess);
    }
    processes_.clear();
}