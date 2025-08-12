# 安装指南

## 概述

此项目现在支持通过 `pip install` 进行安装，包括：
- 自动安装所有依赖
- 提供多个命令行工具
- 支持现有的 Docker 启动脚本和环境变量配置

## 安装方法

### 1. 从源码安装（推荐）

```bash
# 在项目根目录下
pip install .

# 开发模式安装（可编辑）
pip install -e .

# 包含开发依赖
pip install -e ".[dev]"
```

### 2. 使用安装脚本

```bash
./install.sh
```

### 3. 构建分发包

```bash
# 构建 wheel 和 tar.gz
python -m build

# 安装构建的包
pip install dist/microsandbox_mcp_server-1.0.0-py3-none-any.whl
```

## 可用命令

安装后，以下命令将可用：

### 1. `start-localsandbox`
使用 LocalSandbox 配置启动 MCP 服务器：
```bash
start-localsandbox
```

这个命令会：
- 自动查找并加载 `.env.local` 文件
- 检查 Docker 可用性
- 拉取所需的 Docker 镜像
- 设置共享目录
- 启动 HTTP 传输的 MCP 服务器

选项：
```bash
start-localsandbox --env-file /path/to/.env.local  # 指定环境文件
start-localsandbox --skip-docker-check             # 跳过 Docker 检查
start-localsandbox --skip-image-pull               # 跳过镜像拉取
```

### 2. `microsandbox-mcp-server`
标准 MCP 服务器启动命令：
```bash
microsandbox-mcp-server                           # stdio 传输
microsandbox-mcp-server --transport streamable-http --port 8775  # HTTP 传输
microsandbox-mcp-server --transport sse --enable-cors            # SSE 传输
```

### 3. `mcp-server`
`microsandbox-mcp-server` 的简短别名。

## 环境配置

### LocalSandbox 配置文件

项目包含以下配置文件：
- `.env.example` - 配置模板
- `.env.local` - 本地配置文件（需要从模板复制）

使用方法：
```bash
# 复制模板并修改
cp .env.example .env.local
# 编辑配置
vim .env.local
```

### 配置查找顺序

`start-localsandbox` 命令按以下顺序查找 `.env.local` 文件：
1. 当前目录的 `.env.local`
2. 当前目录的 `.env.docker`（向后兼容）
3. `mcp-server/.env.docker`（向后兼容）
4. 安装包目录中的 `.env.local`

## 验证安装

运行测试脚本：
```bash
python test_installation.py
```

或手动测试：
```bash
# 测试命令可用性
microsandbox-mcp-server --help
start-localsandbox --help

# 测试模块导入
python -c "import mcp_server; print('OK')"
python -c "import microsandbox_wrapper; print('OK')"
```

## 兼容性

### 与现有脚本的兼容性

现有的启动脚本 `mcp-server/start_mcp_docker.sh` 仍然可以使用：
```bash
./mcp-server/start_mcp_docker.sh
```

新的 `start-localsandbox` 命令提供相同的功能，但更便于使用。

### 环境变量兼容性

所有现有的环境变量都被支持，包括：
- `MCP_SERVER_HOST`, `MCP_SERVER_PORT`
- `MCP_ENABLE_CORS`
- `LOCALSANDBOX_PYTHON_IMAGE`, `LOCALSANDBOX_NODE_IMAGE`
- `MSB_MAX_SESSIONS`, `MSB_SESSION_TIMEOUT`
- 等等

## 开发

### 开发模式安装

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest tests/
```

### 代码格式化

```bash
black .
flake8 .
mypy .
```

## 故障排除

### 常见问题

1. **命令未找到**
   ```bash
   # 确保 pip 安装路径在 PATH 中
   pip show -f microsandbox-mcp-server
   ```

2. **模块导入错误**
   ```bash
   # 重新安装
   pip uninstall microsandbox-mcp-server
   pip install .
   ```

3. **Docker 相关问题**
   ```bash
   # 检查 Docker 状态
   docker info
   
   # 检查镜像
   docker images
   ```

### 调试

启用详细日志：
```bash
MSB_LOG_LEVEL=DEBUG start-mcp-docker
```

## 文件结构

安装后的包结构：
```
microsandbox-mcp-server/
├── mcp_server/           # MCP 服务器模块
│   ├── main.py          # 主入口点
│   ├── server.py        # 服务器实现
│   └── scripts.py       # 启动脚本
├── microsandbox_wrapper/ # 沙盒包装器
└── sandbox/             # 沙盒 SDK
```

## 下一步

- 查看 [QUICKSTART.md](QUICKSTART.md) 快速开始
- 查看 [README.md](README.md) 了解详细功能
- 运行 `start-localsandbox` 启动服务器