#include "GroupManager.h"
#include <iostream>
#include <zmq.hpp>

int GroupManager::launchGroup(const std::vector<SourceGroup>& launch_groups = {}) {    
    std::vector<SourceGroup> groups_to_launch;
    if (launch_groups.empty()) {
        groups_to_launch = groups;
    } else {
        groups_to_launch = const_cast<std::vector<SourceGroup>&>(launch_groups);
    }
    for (auto& group : groups_to_launch) {
        group.launch();
    }

    return 0;
}

int GroupManager::addGroups(const std::vector<SourceGroup>& add_groups) {
    try {
        groups.insert(groups.end(), add_groups.begin(), add_groups.end());
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] Failed to add groups: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}