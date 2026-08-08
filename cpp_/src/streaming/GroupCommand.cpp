#include "GroupCommand.h"
#include "SourceGroup.h"
#include "GroupOptions.h"

#include <iostream>
#include <unordered_map>
#include <yaml-cpp/yaml.h>

CLI::App* setup_group_command(CLI::App& app, GroupOptions& opts) {
    auto* group_cmd = app.add_subcommand("group", "Launch a predefined group of stream sources");

    group_cmd->add_option("--pth,--path", opts.file_path, "The path to the group configuration file")->default_val("../configs/group_config.yaml");

    return group_cmd;
}

int run_group(const GroupOptions& opts) {
    try {
        std::cout << "[INFO] Config path: " << opts.file_path << std::endl;

        YAML::Node config = YAML::LoadFile(opts.file_path);

        std::cout << "[INFO] Launching Source Group..." << std::endl;

        if (!config["groups"]) {
            std::cerr << "[ERROR] Configuration does not contain 'groups'" << std::endl;
            return 1;
        }

        std::unordered_map<std::string, FieldMap> group;
        std::unordered_map<std::string, double> sync;
        YAML::Node groups = config["groups"];
        
        for (const auto& entry : groups) {
            std::string group_name = entry.first.as<std::string>();
            YAML::Node group_config = entry.second;

            YAML::Node sources = group_config["sources"];
            YAML::Node sync_config = group_config["synchronization"];

            for (const auto& entry : sources) {
                std::string source_name = entry.first.as<std::string>();

                YAML::Node source = entry.second;

                FieldMap fields;

                fields["source_type"] = source["source_type"].as<std::string>();

                fields["port"] = source["port"].as<int>();

                fields["frequency"] = source["frequency"].as<double>();

                fields["ml_model"] = source["ml_model"].as<std::string>();

                fields["data_mode"] = source["data_mode"].as<std::string>();

                fields["serialization"] = source["serialization"].as<std::string>();

                fields["batch_size"] = source["batch_size"].as<int>();

                fields["verbose"] = source["verbose"].as<bool>();

                group[source_name] = std::move(fields);
            }

            SourceGroup sourceGroup(group, sync);
            sourceGroup.launch();

        return 0;
        }
    }

    catch (const YAML::BadFile& e) {
        std::cerr
            << "[ERROR] Could not open YAML configuration file: "
            << opts.file_path << '\n'
            << "[YAML] " << e.what()
            << std::endl;

        return 1;
    }

    catch (const YAML::ParserException& e) {
        std::cerr
            << "[ERROR] Invalid YAML syntax in: "
            << opts.file_path << '\n'
            << "[YAML] " << e.what()
            << std::endl;

        return 1;
    }

    catch (const YAML::BadConversion& e) {
        std::cerr
            << "[ERROR] Invalid value type in YAML configuration.\n"
            << "[YAML] " << e.what()
            << std::endl;

        return 1;
    }

    catch (const YAML::Exception& e) {
        std::cerr
            << "[ERROR] YAML error: "
            << e.what()
            << std::endl;

        return 1;
    }

    catch (const std::exception& e) {
        std::cerr
            << "[ERROR] Unexpected error: "
            << e.what()
            << std::endl;

        return 1;
    }
}