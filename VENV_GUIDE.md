# 虚拟环境使用指南

本项目支持虚拟环境管理，确保依赖隔离和版本一致性。

## 🚀 快速开始

### 方法1: 使用 run.py (推荐)

```bash
# 完整初始化（创建虚拟环境 + 安装依赖 + 配置环境）
python run.py --setup

# 激活虚拟环境后运行
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate.bat  # Windows

# 启动聊天
python run.py --chat
```

### 方法2: 使用平台脚本

**macOS/Linux:**
```bash
# 完整设置
./setup.sh setup

# 激活虚拟环境
source venv/bin/activate

# 运行程序
python run.py --chat
```

**Windows:**
```cmd
# 完整设置
setup.bat setup

# 激活虚拟环境
venv\Scripts\activate.bat

# 运行程序
python run.py --chat
```

## 📋 详细命令说明

### run.py 命令

| 命令 | 说明 |
|------|------|
| `--setup` | 完整初始化（推荐首次使用） |
| `--create-venv` | 仅创建虚拟环境 |
| `--install` | 安装依赖（自动创建虚拟环境） |
| `--venv-info` | 显示虚拟环境信息 |
| `--chat` | 启动聊天模式 |
| `--server` | 启动API服务器 |
| `--test` | 运行测试 |
| `--no-venv` | 跳过虚拟环境检查 |

### 平台脚本命令

| 命令 | setup.sh (Unix) | setup.bat (Windows) |
|------|-----------------|---------------------|
| 完整设置 | `./setup.sh setup` | `setup.bat setup` |
| 创建虚拟环境 | `./setup.sh create` | `setup.bat create` |
| 安装依赖 | `./setup.sh install` | `setup.bat install` |
| 查看信息 | `./setup.sh info` | `setup.bat info` |
| 清理环境 | `./setup.sh clean` | `setup.bat clean` |

## 🔧 常见操作

### 初次使用
```bash
# 1. 克隆项目
git clone <repository-url>
cd multi-agent-framework

# 2. 完整初始化
python run.py --setup

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入API密钥

# 4. 启动使用
python run.py --chat
```

### 日常使用
```bash
# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate.bat  # Windows

# 运行程序
python run.py --chat
python run.py --server
```

### 管理虚拟环境
```bash
# 查看虚拟环境信息
python run.py --venv-info

# 重新安装依赖
python run.py --install

# 清理重建（使用平台脚本）
./setup.sh clean  # 删除虚拟环境
./setup.sh setup  # 重新创建
```

## 🐛 故障排除

### 虚拟环境创建失败
```bash
# 检查Python版本（需要3.8+）
python3 --version

# 手动创建虚拟环境
python3 -m venv venv

# 激活并安装依赖
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 依赖安装失败
```bash
# 激活虚拟环境
source venv/bin/activate

# 升级pip
pip install --upgrade pip

# 分步安装依赖
pip install langgraph
pip install langchain-deepseek
pip install -r requirements.txt
```

### 权限问题 (macOS/Linux)
```bash
# 给脚本添加执行权限
chmod +x setup.sh

# 或直接使用bash运行
bash setup.sh setup
```

## 💡 最佳实践

1. **总是使用虚拟环境**: 避免依赖冲突
2. **定期更新依赖**: `pip install --upgrade -r requirements.txt`
3. **备份配置**: 定期备份 `.env` 文件
4. **清理重建**: 遇到奇怪问题时尝试重建虚拟环境

## 🌟 Tips

- 使用 `python run.py --setup` 是最简单的开始方式
- 虚拟环境位于项目根目录的 `venv/` 文件夹
- 可以使用 `--no-venv` 参数跳过虚拟环境检查
- 平台脚本提供了额外的管理功能（清理、信息查看等）
