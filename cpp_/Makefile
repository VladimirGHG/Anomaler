VCPKG_ROOT = ./vcpkg/installed/arm64-osx
VCPKG_INC  = $(VCPKG_ROOT)/include
VCPKG_LIB  = $(VCPKG_ROOT)/lib

BREW_INC = -I/opt/homebrew/include
BREW_LIB = -L/opt/homebrew/lib

INC = -I./include -I$(VCPKG_INC) $(BREW_INC)
LIB = -L$(VCPKG_LIB) $(BREW_LIB) -lzmq -lCLI11 -lserialport

CXXFLAGS = -std=c++17 $(INC) -Wall

SRC = src/main.cpp \
      src/DataPoint.cpp \
      src/DataStream.cpp \
      src/DataSender.cpp \
      src/SourceFactory.cpp \
      src/sources/RandomSource.cpp \
      src/sources/OutlierSource.cpp \
      src/sources/DriftDecorator.cpp \
      src/sources/SerialSensorSource.cpp
	  
TARGET = builds/main

all:
	@mkdir -p builds
	g++ $(CXXFLAGS) $(SRC) $(LIB) -o $(TARGET)

clean:
	rm -f $(TARGET)