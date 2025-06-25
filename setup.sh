#!/bin/bash
# 虚拟环境管理脚本 (Unix/Linux/macOS)

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查Python版本
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装，请先安装Python 3.8+"
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    print_info "Python版本: $python_version"
    
    if [[ $(echo "$python_version < 3.8" | bc -l) -eq 1 ]]; then
        print_error "需要Python 3.8或更高版本"
        exit 1
    fi
}

# 创建虚拟环境
create_venv() {
    print_info "创建虚拟环境..."
    
    if [ -d "$VENV_DIR" ]; then
        print_warning "虚拟环境已存在: $VENV_DIR"
        return 0
    fi
    
    python3 -m venv "$VENV_DIR"
    print_success "虚拟环境创建成功: $VENV_DIR"
}

# 激活虚拟环境
activate_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        print_error "虚拟环境不存在，请先创建"
        return 1
    fi
    
    source "$VENV_DIR/bin/activate"
    print_success "虚拟环境已激活"
}

# 安装依赖
install_deps() {
    print_info "安装依赖包..."
    
    if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
        print_error "requirements.txt 文件不存在"
        return 1
    fi
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    pip install -r "$PROJECT_DIR/requirements.txt"
    
    print_success "依赖安装完成"
}

# 显示虚拟环境信息
show_info() {
    echo "==================="
    echo "虚拟环境信息"
    echo "==================="
    echo "项目目录: $PROJECT_DIR"
    echo "虚拟环境: $VENV_DIR"
    
    if [ -d "$VENV_DIR" ]; then
        echo "状态: 已创建"
        if [ -f "$VENV_DIR/bin/python" ]; then
            echo "Python路径: $VENV_DIR/bin/python"
            echo "Python版本: $($VENV_DIR/bin/python --version)"
        fi
        
        # 显示已安装包数量
        if [ -f "$VENV_DIR/bin/pip" ]; then
            package_count=$($VENV_DIR/bin/pip list --format=json | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
            echo "已安装包数量: $package_count"
        fi
    else
        echo "状态: 未创建"
    fi
    
    echo "==================="
}

# 清理虚拟环境
clean_venv() {
    if [ -d "$VENV_DIR" ]; then
        read -p "确定要删除虚拟环境吗? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_DIR"
            print_success "虚拟环境已删除"
        else
            print_info "操作已取消"
        fi
    else
        print_warning "虚拟环境不存在"
    fi
}

# 完整设置
full_setup() {
    print_info "开始完整设置..."
    
    check_python
    create_venv
    activate_venv
    install_deps
    
    print_success "完整设置完成!"
    print_info "激活虚拟环境: source venv/bin/activate"
    print_info "运行程序: python run.py --chat"
}

# 显示使用帮助
show_help() {
    echo "虚拟环境管理脚本"
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  setup     - 完整设置（创建虚拟环境+安装依赖）"
    echo "  create    - 创建虚拟环境"
    echo "  install   - 安装依赖包"
    echo "  info      - 显示虚拟环境信息"
    echo "  clean     - 删除虚拟环境"
    echo "  activate  - 显示激活命令"
    echo "  help      - 显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 setup     # 完整设置"
    echo "  $0 info      # 查看信息"
    echo "  source venv/bin/activate  # 激活虚拟环境"
}

# 主函数
main() {
    cd "$PROJECT_DIR"
    
    case "${1:-help}" in
        "setup")
            full_setup
            ;;
        "create")
            check_python
            create_venv
            ;;
        "install")
            if [ ! -d "$VENV_DIR" ]; then
                print_error "虚拟环境不存在，请先运行: $0 create"
                exit 1
            fi
            activate_venv
            install_deps
            ;;
        "info")
            show_info
            ;;
        "clean")
            clean_venv
            ;;
        "activate")
            if [ -d "$VENV_DIR" ]; then
                echo "source $VENV_DIR/bin/activate"
            else
                print_error "虚拟环境不存在"
            fi
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

main "$@"
