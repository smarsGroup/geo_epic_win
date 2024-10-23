@echo off
setlocal enabledelayedexpansion

:: Environment name
set ENV_NAME=epic_env
set ANACONDA_INSTALLER=Anaconda3-2023.09-0-Windows-x86_64.exe
set ANACONDA_URL=https://repo.anaconda.com/archive/%ANACONDA_INSTALLER%
set GITHUB_PACKAGE_URL=git+https://github.com/smarsGroup/geo_epic_win.git

:: Function to check if conda is installed
call :check_conda_installed
if %ERRORLEVEL% neq 0 (
    echo Conda is not installed. Installing Anaconda...
    call :install_anaconda
) else (
    echo Conda is installed.
)

:: Check if the environment exists, if not create it
call :check_env_exists
if %ERRORLEVEL% neq 0 (
    call :create_env
) else (
    :: If environment exists, install the GitHub package via pip
    echo Updating geo_epic package...
    call conda activate %ENV_NAME%
    call pip uninstall -y geo-epic
    call pip install %GITHUB_PACKAGE_URL%
    call conda deactivate
)

:: Activate the environment
echo Activating environment '%ENV_NAME%'...
call conda activate %ENV_NAME%
call geo_epic init
echo Environment '%ENV_NAME%' is activated.

goto :eof

:check_conda_installed
where conda >nul 2>&1
if %ERRORLEVEL% neq 0 exit /b 1
exit /b 0

:install_anaconda
if not exist %ANACONDA_INSTALLER% (
    echo Downloading Anaconda installer...
    powershell -Command "(New-Object Net.WebClient).DownloadFile('%ANACONDA_URL%', '%ANACONDA_INSTALLER%')"
)

echo Installing Anaconda...
start /wait "" %ANACONDA_INSTALLER% /InstallationType=JustMe /AddToPath=1 /RegisterPython=1 /S /D=%UserProfile%\Anaconda3

:: Initialize Conda for the current shell
call %UserProfile%\Anaconda3\Scripts\activate.bat

:: Initialize Conda for future shell sessions
call conda init
echo Anaconda installation complete. Please restart your command prompt.
exit /b 0

:check_env_exists
conda env list | findstr /C:"%ENV_NAME%" >nul
if %ERRORLEVEL% equ 0 (
    echo Conda environment '%ENV_NAME%' already exists.
    exit /b 0
) else (
    echo Conda environment '%ENV_NAME%' does not exist.
    exit /b 1
)

:create_env
echo Creating Conda environment '%ENV_NAME%' ...
call conda env create -f https://raw.githubusercontent.com/smarsGroup/geo_epic_win/main/docs/conda_env.yml
exit /b 0