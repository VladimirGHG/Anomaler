VCPKG_ROOT = ./vcpkg/installed/arm64-osx
VCPKG_INC = $(VCPKG_ROOT)/include
VCPKG_LIB = $(VCPKG_ROOT)/lib

FLATC = $(VCPKG_ROOT)/tools/flatbuffers/flatc

BREW_INC = -I/opt/homebrew/include
BREW_LIB = -L/opt/homebrew/lib

INC = -I./include \
      -I./include/cli \
      -I./include/sources \
      -I./include/streaming \
      -I$(VCPKG_INC) \
      $(BREW_INC)
      
LIB = -L$(VCPKG_LIB) $(BREW_LIB) -lzmq -lCLI11 -lcserialport -lyaml-cpp -framework CoreFoundation -framework IOKit
CXXFLAGS = -std=c++17 $(INC) -Wall

SCHEMA = schema/telemetry.fbs
GEN_HEADER = include/telemetry_generated.h

SRC = src/main.cpp \
      src/DataPoint.cpp \
      src/DataStream.cpp \
      src/DataSender.cpp \
      src/SourceFactory.cpp \
      src/SourceGroup.cpp \
      src/GroupManager.cpp \
      src/sources/RandomSource.cpp \
      src/sources/OutlierSource.cpp \
      src/sources/DriftDecorator.cpp \
      src/sources/SerialSensorSource.cpp \
      src/cli/StreamCommand.cpp \
      src/streaming/GroupCommand.cpp \
      src/streaming/PollingLoop.cpp \
      src/streaming/DataSenderFactory.cpp \
      src/streaming/ManagerHandshake.cpp \
      src/streaming/GroupManagerHandshake.cpp
TARGET = builds/main

all: $(GEN_HEADER)
	@mkdir -p builds
	g++ $(CXXFLAGS) $(SRC) $(LIB) -o $(TARGET)

$(GEN_HEADER): $(SCHEMA)
	@echo "Compiling FlatBuffers schema..."
	@mkdir -p include
	$(FLATC) --cpp -o include $(SCHEMA)

clean:
	rm -f $(TARGET) $(GEN_HEADER)