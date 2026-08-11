#ifndef GROUP_MANAGER_H
#define GROUP_MANAGER_H

#include <string>
#include <vector>
#include "SourceGroup.h"

class GroupManager {
public:

    GroupManager() = default;

    // Launches all if no group name is provided, otherwise launches the specified group.
    int launchGroup(const std::vector<SourceGroup>& launch_groups);
    
    int addGroups(const std::vector<SourceGroup>& add_groups);
    int removeGroups(const std::vector<SourceGroup>& remove_groups);

    std::vector<SourceGroup> groups;
    
};

#endif