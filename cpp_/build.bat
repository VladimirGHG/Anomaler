@echo off
setlocal

call "C:\Program Files\Microsoft Visual Studio\18\Insiders\Common7\Tools\VsDevCmd.bat" -arch=x64

echo Compiling FlatBuffers schema...
if not exist include mkdir include
vcpkg\installed\x64-windows\tools\flatbuffers\flatc.exe --cpp -o include schema/telemetry.fbs
if errorlevel 1 (
    echo FlatBuffers compilation failed!
    exit /b 1
)

if not exist builds mkdir builds

set INC=/I ./include /I ./src/cli /I ./src/streaming /I ./vcpkg/installed/x64-windows/include
set LIB_PATH=/LIBPATH:./vcpkg/installed/x64-windows/lib

echo Compiling C++ Application...
cl /std:c++17 /EHsc /MD /DCLI11_PRECOMPILED %INC% /Fo:builds\ ^
    src/main.cpp ^
    src/DataPoint.cpp ^
    src/DataStream.cpp ^
    src/DataSender.cpp ^
    src/SourceFactory.cpp ^
    src/SourceGroup.cpp ^
    src/sources/RandomSource.cpp ^
    src/sources/OutlierSource.cpp ^
    src/sources/DriftDecorator.cpp ^
    src/sources/SerialSensorSource.cpp ^
    src/cli/StreamCommand.cpp ^
    src/streaming/GroupCommand.cpp ^
    src/streaming/PollingLoop.cpp ^
    src/streaming/DataSenderFactory.cpp ^
    src/streaming/ManagerHandshake.cpp ^
    /link %LIB_PATH% libzmq-mt-4_3_5.lib libcserialport.lib CLI11.lib Shell32.lib /OUT:builds/main.exe
if errorlevel 1 (
    echo Build failed!
    exit /b 1
)

xcopy /y vcpkg\installed\x64-windows\bin\*.dll builds\ >nul

echo Done!
endlocal