@echo off
echo ====================================
echo WSL to Windows Connection Fix Script
echo ====================================
echo This script will configure Windows Firewall to allow WSL connections.
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

echo Adding firewall rules for WSL...

REM Create inbound rules for common Flutter development ports
netsh advfirewall firewall add rule name="WSL Flutter Web 8080" dir=in action=allow protocol=TCP localport=8080
netsh advfirewall firewall add rule name="WSL Flutter Web 8090" dir=in action=allow protocol=TCP localport=8090
netsh advfirewall firewall add rule name="WSL Flutter Web 8091" dir=in action=allow protocol=TCP localport=8091
netsh advfirewall firewall add rule name="WSL Flutter Web 9090" dir=in action=allow protocol=TCP localport=9090
netsh advfirewall firewall add rule name="WSL Flutter Web 9100" dir=in action=allow protocol=TCP localport=9100

echo.
echo Configuring WSL network...

REM Get WSL IP from WSL
echo Attempting to get WSL IP address...
wsl -- hostname -I > %TEMP%\wsl_ip.txt
set /p WSL_IP=<%TEMP%\wsl_ip.txt
echo WSL IP: %WSL_IP%

echo.
echo Testing connection to WSL...
ping -n 3 %WSL_IP%

echo.
echo All set\! Please try accessing your Flutter app at:
echo http://%WSL_IP%:8090
echo.
echo Press any key to exit...
pause > nul
