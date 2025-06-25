#!/usr/bin/env python3
"""
快速启动脚本
支持虚拟环境管理和依赖安装
"""

import os
import sys
import subprocess
import argparse
import venv
import platform
from pathlib import Path

def get_venv_path():
    """获取虚拟环境路径"""
    return Path("venv")

def get_python_executable():
    """获取Python可执行文件路径"""
    venv_path = get_venv_path()
    if platform.system() == "Windows":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"
    
    return python_exe if python_exe.exists() else sys.executable

def get_pip_executable():
    """获取pip可执行文件路径"""
    venv_path = get_venv_path()
    if platform.system() == "Windows":
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:
        pip_exe = venv_path / "bin" / "pip"
    
    return pip_exe if pip_exe.exists() else "pip"

def create_virtual_environment():
    """创建虚拟环境"""
    venv_path = get_venv_path()
    
    if venv_path.exists():
        print(f"虚拟环境已存在: {venv_path}")
        return True
    
    print(f"创建虚拟环境: {venv_path}")
    try:
        # 使用python3 -m venv创建虚拟环境
        import sys
        python_cmd = sys.executable
        
        # 尝试使用python3命令（对于某些系统更可靠）
        result = subprocess.run(["python3", "-m", "venv", str(venv_path)], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            # 如果python3失败，尝试使用当前Python解释器
            print("使用python3失败，尝试使用当前Python解释器...")
            result = subprocess.run([python_cmd, "-m", "venv", str(venv_path)], 
                                  capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 虚拟环境创建成功")
            
            # 验证虚拟环境是否正确创建
            python_exe = get_python_executable()
            if python_exe.exists():
                print(f"虚拟环境Python路径: {python_exe}")
                return True
            else:
                print(f"❌ 虚拟环境Python文件不存在: {python_exe}")
                return False
        else:
            print(f"❌ 虚拟环境创建失败:")
            print(f"输出: {result.stdout}")
            print(f"错误: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 虚拟环境创建异常: {e}")
        return False

def check_virtual_environment():
    """检查虚拟环境是否存在"""
    venv_path = get_venv_path()
    python_exe = get_python_executable()
    
    if not venv_path.exists():
        print("❌ 虚拟环境未找到")
        return False
    
    if not python_exe.exists():
        print("❌ 虚拟环境Python可执行文件未找到")
        return False
    
    print(f"✅ 虚拟环境已准备就绪: {venv_path}")
    return True

def install_dependencies(minimal=False):
    """在虚拟环境中安装依赖"""
    venv_path = get_venv_path()
    
    # 检查或创建虚拟环境
    if not venv_path.exists():
        if not create_virtual_environment():
            return False
    
    # 确保使用虚拟环境中的Python
    python_exe = get_python_executable()
    if not python_exe.exists():
        print(f"❌ 虚拟环境Python不存在: {python_exe}")
        return False
    
    requirements_file = "requirements-minimal.txt" if minimal else "requirements.txt"
    print(f"正在安装依赖包 ({'最小版本' if minimal else '完整版本'})...")
    print(f"使用Python: {python_exe}")
    print(f"依赖文件: {requirements_file}")
    
    try:
        # 首先升级pip（使用虚拟环境中的pip）
        print("升级pip...")
        result = subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], 
                              capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"pip升级输出: {result.stdout}")
            print(f"pip升级错误: {result.stderr}")
            # pip升级失败不是致命错误，继续安装依赖
            print("⚠️ pip升级失败，但继续安装依赖...")
        
        # 安装requirements.txt中的依赖（使用虚拟环境中的pip）
        print("安装项目依赖...")
        
        # 添加超时和实时输出
        process = subprocess.Popen(
            [str(python_exe), "-m", "pip", "install", "-r", requirements_file, "-v"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # 实时输出安装过程
        output_lines = []
        try:
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(f"  {output.strip()}")
                    output_lines.append(output.strip())
        except KeyboardInterrupt:
            print("\n⚠️ 用户中断安装过程")
            process.terminate()
            return False
        
        return_code = process.poll()
        
        if return_code == 0:
            print("✅ 依赖安装完成!")
            return True
        else:
            print(f"❌ 依赖安装失败 (返回码: {return_code})")
            print("最后几行输出:")
            for line in output_lines[-10:]:
                print(f"  {line}")
            
            # 如果不是最小安装且失败了，建议尝试最小安装
            if not minimal:
                print("\n💡 建议: 尝试最小依赖安装:")
                print("   python run.py --install-minimal")
            
            return False
        
    except subprocess.TimeoutExpired:
        print("❌ 安装超时（2分钟），可能网络连接有问题")
        return False
    except FileNotFoundError as e:
        print(f"❌ 找不到文件: {e}")
        print("请确保虚拟环境正确创建")
        return False
    except Exception as e:
        print(f"❌ 安装过程中出现错误: {e}")
        return False

def show_venv_info():
    """显示虚拟环境信息"""
    venv_path = get_venv_path()
    python_exe = get_python_executable()
    
    if not venv_path.exists():
        print("❌ 虚拟环境未创建")
        return
    
    print(f"虚拟环境路径: {venv_path.absolute()}")
    print(f"Python路径: {python_exe}")
    
    # 显示已安装包
    try:
        result = subprocess.run([str(python_exe), "-m", "pip", "list"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("\n已安装的包:")
            print(result.stdout)
    except Exception as e:
        print(f"获取包列表失败: {e}")

def get_activation_command():
    """获取虚拟环境激活命令"""
    venv_path = get_venv_path()
    
    if platform.system() == "Windows":
        if os.environ.get("SHELL") or os.environ.get("COMSPEC", "").endswith("powershell.exe"):
            return f"{venv_path}\\Scripts\\Activate.ps1"
        else:
            return f"{venv_path}\\Scripts\\activate.bat"
    else:
        return f"source {venv_path}/bin/activate"

def create_env_file():
    """创建环境变量文件"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        print("创建环境变量文件...")
        env_file.write_text(env_example.read_text())
        print("请编辑 .env 文件，填入相应的API密钥")
        return False
    return True

def create_data_directories():
    """创建数据目录"""
    data_dirs = [
        "data",
        "data/chroma",
        "data/memory"
    ]
    
    for dir_path in data_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print("数据目录创建完成")

def main():
    parser = argparse.ArgumentParser(description="多Agent框架快速启动")
    parser.add_argument("--create-venv", action="store_true", help="创建虚拟环境")
    parser.add_argument("--install", action="store_true", help="安装完整依赖（自动创建虚拟环境）")
    parser.add_argument("--install-minimal", action="store_true", help="安装最小依赖（适用于网络问题或快速测试）")
    parser.add_argument("--setup", action="store_true", help="完整初始化设置（创建虚拟环境+安装依赖+配置）")
    parser.add_argument("--setup-minimal", action="store_true", help="最小初始化设置（使用最小依赖）")
    parser.add_argument("--venv-info", action="store_true", help="显示虚拟环境信息")
    parser.add_argument("--chat", action="store_true", help="启动聊天模式")
    parser.add_argument("--server", action="store_true", help="启动API服务器")
    parser.add_argument("--test", action="store_true", help="运行测试")
    parser.add_argument("--example", choices=["medical", "travel", "research"], help="运行示例")
    parser.add_argument("--no-venv", action="store_true", help="不使用虚拟环境运行")
    
    args = parser.parse_args()
    
    # 确保在正确的目录中运行
    os.chdir(Path(__file__).parent)
    
    if args.create_venv:
        create_virtual_environment()
        return
    
    if args.venv_info:
        show_venv_info()
        return
    
    if args.install:
        if install_dependencies(minimal=False):
            print("\n✅ 完整依赖安装完成!")
            print(f"激活虚拟环境命令: {get_activation_command()}")
        return
    
    if args.install_minimal:
        if install_dependencies(minimal=True):
            print("\n✅ 最小依赖安装完成!")
            print(f"激活虚拟环境命令: {get_activation_command()}")
            print("\n⚠️ 注意: 这是最小安装，某些功能可能不可用")
            print("如需完整功能，请稍后运行: python run.py --install")
        return
    
    if args.setup or args.setup_minimal:
        minimal = args.setup_minimal
        print(f"🚀 开始{'最小' if minimal else '完整'}初始化设置...")
        
        # 1. 创建虚拟环境并安装依赖
        if not install_dependencies(minimal=minimal):
            print("❌ 依赖安装失败，停止设置")
            return
        
        # 2. 创建数据目录
        create_data_directories()
        
        # 3. 创建环境文件
        env_ready = create_env_file()
        
        if env_ready:
            print(f"\n✅ {'最小' if minimal else '完整'}初始化设置完成!")
            print(f"激活虚拟环境: {get_activation_command()}")
            print("现在可以运行: python run.py --chat")
        else:
            print(f"\n⚠️  {'最小' if minimal else '完整'}初始化基本完成，请先配置 .env 文件中的API密钥")
            print(f"激活虚拟环境: {get_activation_command()}")
        
        if minimal:
            print("\n⚠️ 这是最小安装，某些功能可能不可用")
            print("如需完整功能，请稍后运行: python run.py --install")
        
        return
    
    # 对于运行命令，检查虚拟环境（除非明确指定不使用）
    if not args.no_venv:
        venv_path = get_venv_path()
        if not venv_path.exists():
            print("❌ 虚拟环境未找到，请先运行:")
            print("   python run.py --setup")
            return
    
    # 获取正确的Python可执行文件
    python_exe = sys.executable if args.no_venv else get_python_executable()
    
    if args.chat:
        print("启动聊天模式...")
        if not args.no_venv:
            print(f"使用虚拟环境: {get_venv_path()}")
        subprocess.run([str(python_exe), "-m", "src.cli.main", "chat"])
        return
    
    if args.server:
        print("启动API服务器...")
        if not args.no_venv:
            print(f"使用虚拟环境: {get_venv_path()}")
        subprocess.run([str(python_exe), "-m", "src.cli.main", "server"])
        return
    
    if args.test:
        print("运行框架测试...")
        if not args.no_venv:
            print(f"使用虚拟环境: {get_venv_path()}")
        subprocess.run([str(python_exe), "-m", "src.cli.main", "test"])
        return
    
    if args.example:
        print(f"运行{args.example}示例...")
        if not args.no_venv:
            print(f"使用虚拟环境: {get_venv_path()}")
        example_map = {
            "medical": "examples.medical_agent",
            "travel": "examples.travel_agent", 
            "research": "examples.research_agent"
        }
        subprocess.run([str(python_exe), "-m", example_map[args.example]])
        return
    
    # 默认显示帮助
    parser.print_help()
    print("\n🚀 快速开始指南:")
    print("="*50)
    print("1️⃣  初始化项目 (推荐)")
    print("   python run.py --setup          # 完整安装")
    print("   python run.py --setup-minimal  # 最小安装（网络慢时使用）")
    print("")
    print("2️⃣  或者分步骤设置:")
    print("   python run.py --create-venv       # 创建虚拟环境")
    print("   python run.py --install           # 安装完整依赖")
    print("   python run.py --install-minimal   # 安装最小依赖")
    print("")
    print("3️⃣  运行程序:")
    print("   python run.py --chat              # 启动聊天模式")
    print("   python run.py --server            # 启动API服务器")
    print("")
    print("🔧 其他命令:")
    print("   python run.py --venv-info         # 查看虚拟环境信息")
    print("   python run.py --test              # 运行测试")
    print("   python run.py --example medical   # 运行示例")
    print("")
    print("💡 提示:")
    print("   - 首次使用请先运行 --setup 或 --setup-minimal")
    print("   - 如果网络慢或某些包安装失败，使用 --setup-minimal")
    print("   - 使用 --no-venv 参数可跳过虚拟环境检查")
    print(f"   - 虚拟环境激活命令: {get_activation_command()}")
    print("   - 按 Ctrl+C 可中断长时间的安装过程")

if __name__ == "__main__":
    main()
