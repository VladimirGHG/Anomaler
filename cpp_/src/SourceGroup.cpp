#include "SourceGroup.h"
#include <iostream>
#include <sstream>
#include <vector>
#include <cstring>
#include <zmq.hpp>

#ifndef _WIN32
  #include <sys/types.h>
  #include <sys/wait.h>
  #include <unistd.h>
  #include <signal.h>
#endif

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

        std::vector<std::string> args;

    #ifdef _WIN32
        args.push_back(".\\builds\\main");
    #else
        args.push_back("./builds/main");
    #endif
        args.push_back("stream");

        // Compose the arguments from whatever fields are actually present.
        for (const auto& [field, flag] : kFieldToFlag) {
            if (field == "verbose") continue;
            auto it = attributes.find(field);
            if (it == attributes.end()) continue;
            args.push_back(flag);
            args.push_back(valueToString(it->second));
        }
        
        if (auto vIt = attributes.find("verbose"); vIt != attributes.end()) {
            if (const bool* b = std::get_if<bool>(&vIt->second); b && *b) {
                args.push_back("-v");
            }
        }

    #ifdef _WIN32
        std::ostringstream command;
        for (size_t i = 0; i < args.size(); ++i) {
            if (i > 0) command << " ";
            command << args[i];
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
    #else
        pid_t pid = fork();
        if (pid < 0) {
            std::cerr << "[ERROR] Failed to fork process for source: " << source_name << std::endl;
            continue;
        }

        if (pid == 0) {
            // Child process
            std::vector<char*> c_args;
            for (auto& arg : args) {
                c_args.push_back(arg.data());
            }
            c_args.push_back(nullptr);

            execvp(c_args[0], c_args.data());
            std::cerr << "[ERROR] execvp failed for source: " << source_name << std::endl;
            _exit(1);
        } else {
            // Parent process
            std::cout << "[INFO] Launched source '" << source_name << "' as PID " << pid << std::endl;
            processes_.push_back(pid);
        }
    #endif
    }
}

void SourceGroup::waitAll() {
    if (processes_.empty()) return;

    #ifdef _WIN32
        std::vector<HANDLE> handles;
        for (auto& pi : processes_) handles.push_back(pi.hProcess);

        WaitForMultipleObjects(static_cast<DWORD>(handles.size()), handles.data(), TRUE, INFINITE);

        for (auto& pi : processes_) {
            DWORD exitCode = 0;
            GetExitCodeProcess(pi.hProcess, &exitCode);
            std::cout << "[INFO] PID " << pi.dwProcessId << " exited with code " << exitCode << std::endl;
            CloseHandle(pi.hProcess);
        }
    #else
        for (pid_t pid : processes_) {
            int status = 0;
            waitpid(pid, &status, 0);
            int exitCode = WIFEXITED(status) ? WEXITSTATUS(status) : -1;
            std::cout << "[INFO] PID " << pid << " exited with code " << exitCode << std::endl;
        }
    #endif
        processes_.clear();
}

void SourceGroup::terminateAll() {
    for (auto& proc : processes_) {
    #ifdef _WIN32
            TerminateProcess(proc.hProcess, 0);
            CloseHandle(proc.hProcess);
    #else
            kill(proc, SIGTERM);
    #endif
    }
    processes_.clear();
}