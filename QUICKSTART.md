# 快速开始指南

## 安装

### 方法 1: 从源码安装（推荐）

```bash
# 克隆仓库
git clone <repository-url>
cd <repository-name>

# 安装包和依赖
pip install .

# 或者开发模式安装
pip install -e ".[dev]"
```

### 方法 2: 使用安装脚本

```bash
./install.sh
```

## 验证安装

运行测试脚本验证安装是否成功：

```bash
python test_installation.py
```

## 启动 MCP 服务器

### 使用 LocalSandbox（推荐）

1. 确保 Docker 已安装并运行
2. 复制环境配置文件：
   ```bash
   cp .env.example .env.local
   ```
3. 根据需要修改 `.env.local` 文件
4. 启动服务器：
   ```bash
   start-localsandbox
   ```

### 使用标准 MCP 协议

```bash
# stdio 传输（用于 MCP 客户端）
microsandbox-mcp-server

# HTTP 传输
microsandbox-mcp-server --transport streamable-http --port 8775

# SSE 传输
microsandbox-mcp-server --transport sse --enable-cors
```

## 配置说明

### LocalSandbox 配置

主要配置项在 `.env.local` 文件中：

```bash
# 服务器配置
MCP_SERVER_PORT=8775
MCP_ENABLE_CORS=true

# Docker 镜像
LOCALSANDBOX_PYTHON_IMAGE=python:3.11-slim
LOCALSANDBOX_NODE_IMAGE=node:18-slim

# 会话管理
MSB_MAX_SESSIONS=5
MSB_SESSION_TIMEOUT=3600

# 卷映射（将主机目录映射到容器）
MSB_SHARED_VOLUME_PATH='["/path/to/host/dir:/workspace"]'
```

### 命令行选项

```bash
# 查看所有选项
microsandbox-mcp-server --help

# LocalSandbox 启动选项
start-localsandbox --help
```

## 测试服务器

启动服务器后，可以通过以下方式测试：

### HTTP 传输测试

```bash
curl http://localhost:8775/health
```

### 在项目根目录启动

如果你在项目根目录下，可以直接运行：

```bash
# 使用现有的启动脚本
./mcp-server/start_mcp_docker.sh

# 或使用安装的命令
start-mcp-docker
```

## 故障排除

### 常见问题

1. **Docker 未运行**
   ```bash
   # 启动 Docker
   # macOS: 打开 Docker Desktop
   # Linux: sudo systemctl start docker
   ```

2. **端口被占用**
   ```bash
   # 检查端口使用情况
   lsof -i :8775
   
   # 使用不同端口
   start-localsandbox --env-file .env.local
   # 然后修改 .env.local 中的 MCP_SERVER_PORT
   ```

3. **权限问题**
   ```bash
   # 确保用户在 docker 组中（Linux）
   sudo usermod -aG docker $USER
   # 重新登录或重启
   ```

4. **Python 包导入错误**
   ```bash
   # 重新安装
   pip uninstall microsandbox-mcp-server
   pip install .
   ```

### 调试模式

启用详细日志：

```bash
# 修改 .env.local
MSB_LOG_LEVEL=DEBUG

# 或使用环境变量
MSB_LOG_LEVEL=DEBUG start-localsandbox
```

## 下一步

- 查看 [README.md](README.md) 了解详细功能
- 查看 [mcp-server/README.md](mcp-server/README.md) 了解 MCP 服务器详情
- 查看 [python/README.md](python/README.md) 了解沙盒 SDK 详情