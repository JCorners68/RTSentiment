@echo off
echo ======================================
echo WSL Port Forwarding Script
echo ======================================
echo This script will forward WSL ports to Windows.
echo.

REM Run with administrative privileges
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo Requesting administrative privileges...
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    if exist "%temp%\getadmin.vbs" ( del "%temp%\getadmin.vbs" )
    pushd "%CD%"
    CD /D "%~dp0"

echo Getting WSL IP address...
wsl -- hostname -I > %TEMP%\wsl_ip.txt
set /p WSL_IP=<%TEMP%\wsl_ip.txt
echo WSL IP: %WSL_IP%

echo.
echo Setting up port forwarding...
netsh interface portproxy add v4tov4 listenport=9000 listenaddress=0.0.0.0 connectport=8888 connectaddress=%WSL_IP%
netsh interface portproxy add v4tov4 listenport=9001 listenaddress=0.0.0.0 connectport=7777 connectaddress=%WSL_IP%
netsh interface portproxy add v4tov4 listenport=9002 listenaddress=0.0.0.0 connectport=9090 connectaddress=%WSL_IP%

echo.
echo Port forwarding set up:
echo - WSL port 8888 -> Windows port 9000
echo - WSL port 7777 -> Windows port 9001
echo - WSL port 9090 -> Windows port 9002
echo.
echo Test with these URLs:
echo http://localhost:9000
echo http://localhost:9001
echo http://localhost:9002
echo.

echo Current port proxies:
netsh interface portproxy show v4tov4

echo.
echo Press any key to exit...
pause > nul