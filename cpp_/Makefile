VCPKG_INC = ./vcpkg/installed/arm64-osx/include
VCPKG_LIB = ./vcpkg/installed/arm64-osx/lib
INC = -I./include -I$(VCPKG_INC)
LIB = -L$(VCPKG_LIB) -lzmq

SRC = src/main.cpp src/DataPoint.cpp src/DataStream.cpp src/DataSender.cpp

TARGET = builds/main

all:
	@mkdir -p builds
	g++ -std=c++17 $(INC) $(SRC) $(LIB) -o $(TARGET)

clean:
	rm -f $(TARGET)