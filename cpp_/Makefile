VCPKG_ROOT = ./vcpkg/installed/arm64-osx
VCPKG_INC  = $(VCPKG_ROOT)/include
VCPKG_LIB  = $(VCPKG_ROOT)/lib

INC = -I./include -I$(VCPKG_INC)
LIB = -L$(VCPKG_LIB) -lzmq -lCLI11 

CXXFLAGS = -std=c++17 $(INC) -Wall

SRC = src/main.cpp \
      src/DataPoint.cpp \
      src/DataStream.cpp \
      src/DataSender.cpp \
      src/SourceFactory.cpp \
      src/sources/RandomSource.cpp \
      src/sources/OutlierSource.cpp \
      src/sources/DriftDecorator.cpp
	  
TARGET = builds/main

all:
	@mkdir -p builds
	g++ $(CXXFLAGS) $(SRC) $(LIB) -o $(TARGET)

clean:
	rm -f $(TARGET)