@echo off
REM 虚拟环境管理脚本 (Windows)

setlocal enabledelayedexpansion

set "PROJECT_DIR=%~dp0"
set "VENV_DIR=%PROJECT_DIR%venv"

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装，请先安装Python 3.8+
    pause
    exit /b 1
)

REM 获取命令行参数
set "COMMAND=%1"
if "%COMMAND%"=="" set "COMMAND=help"

if "%COMMAND%"=="setup" goto :full_setup
if "%COMMAND%"=="create" goto :create_venv
if "%COMMAND%"=="install" goto :install_deps
if "%COMMAND%"=="info" goto :show_info
if "%COMMAND%"=="clean" goto :clean_venv
if "%COMMAND%"=="activate" goto :show_activate
goto :show_help

:create_venv
echo ℹ️  创建虚拟环境...
if exist "%VENV_DIR%" (
    echo ⚠️  虚拟环境已存在: %VENV_DIR%
    goto :eof
)

python -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo ❌ 虚拟环境创建失败
    pause
    exit /b 1
)

echo ✅ 虚拟环境创建成功: %VENV_DIR%
goto :eof

:install_deps
echo ℹ️  安装依赖包...

if not exist "%VENV_DIR%" (
    echo ❌ 虚拟环境不存在，请先运行: %~nx0 create
    pause
    exit /b 1
)

if not exist "%PROJECT_DIR%requirements.txt" (
    echo ❌ requirements.txt 文件不存在
    pause
    exit /b 1
)

REM 激活虚拟环境并安装依赖
call "%VENV_DIR%\Scripts\activate.bat" && (
    python -m pip install --upgrade pip
    pip install -r "%PROJECT_DIR%requirements.txt"
    if !errorlevel! equ 0 (
        echo ✅ 依赖安装完成
    ) else (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
)
goto :eof

:show_info
echo ===================
echo 虚拟环境信息
echo ===================
echo 项目目录: %PROJECT_DIR%
echo 虚拟环境: %VENV_DIR%

if exist "%VENV_DIR%" (
    echo 状态: 已创建
    if exist "%VENV_DIR%\Scripts\python.exe" (
        echo Python路径: %VENV_DIR%\Scripts\python.exe
        "%VENV_DIR%\Scripts\python.exe" --version 2>nul && echo Python版本: !
    )
) else (
    echo 状态: 未创建
)

echo ===================
goto :eof

:clean_venv
if exist "%VENV_DIR%" (
    set /p "confirm=确定要删除虚拟环境吗? (y/N): "
    if /i "!confirm!"=="y" (
        rmdir /s /q "%VENV_DIR%"
        echo ✅ 虚拟环境已删除
    ) else (
        echo ℹ️  操作已取消
    )
) else (
    echo ⚠️  虚拟环境不存在
)
goto :eof

:show_activate
if exist "%VENV_DIR%" (
    echo %VENV_DIR%\Scripts\activate.bat
) else (
    echo ❌ 虚拟环境不存在
)
goto :eof

:full_setup
echo ℹ️  开始完整设置...

call :create_venv
if errorlevel 1 exit /b 1

call :install_deps
if errorlevel 1 exit /b 1

echo.
echo ✅ 完整设置完成!
echo ℹ️  激活虚拟环境: %VENV_DIR%\Scripts\activate.bat
echo ℹ️  运行程序: python run.py --chat
goto :eof

:show_help
echo 虚拟环境管理脚本 (Windows)
echo 用法: %~nx0 [命令]
echo.
echo 命令:
echo   setup     - 完整设置（创建虚拟环境+安装依赖）
echo   create    - 创建虚拟环境
echo   install   - 安装依赖包
echo   info      - 显示虚拟环境信息
echo   clean     - 删除虚拟环境
echo   activate  - 显示激活命令
echo   help      - 显示此帮助信息
echo.
echo 示例:
echo   %~nx0 setup     # 完整设置
echo   %~nx0 info      # 查看信息
echo   %VENV_DIR%\Scripts\activate.bat  # 激活虚拟环境
echo.
pause
goto :eof
