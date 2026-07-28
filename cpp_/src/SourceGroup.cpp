#include "SourceGroup.h"
#include <iostream>

void SourceGroup::launch() {
    for (const auto& [source_type_name, port_frequency_array] : group_) {
        const std::string& source_type = source_type_name[0];
        const std::string& source_name = source_type_name[1];
        int port = port_frequency_array.first;
        double frequency = port_frequency_array.second;

        std::string command = ".\\builds\\main stream -p " + std::to_string(port) +
                               " -f " + std::to_string(frequency) +
                               " -s " + source_type;

        STARTUPINFOA si{};
        si.cb = sizeof(si);
        PROCESS_INFORMATION pi{};

        std::vector<char> cmdBuf(command.begin(), command.end());
        cmdBuf.push_back('\0');

        BOOL ok = CreateProcessA(
            nullptr, // application name (use nullptr, pass exe in cmdline)
            cmdBuf.data(), // mutable command line
            nullptr, nullptr, // process/thread security attrs
            FALSE, // inherit handles
            CREATE_NEW_CONSOLE, // give each source its own console window
            nullptr, // environment
            nullptr, // current directory
            &si, &pi
        );

        if (!ok) {
            std::cerr << "[ERROR] Failed to launch source: " << source_name
                       << " (error " << GetLastError() << ") with command: "
                       << command << std::endl;
            continue;
        }

        std::cout << "[INFO] Launched source '" << source_name
                   << "' as PID " << pi.dwProcessId << std::endl;

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