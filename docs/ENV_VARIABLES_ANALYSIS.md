# MCP Server Docker 环境变量配置分析

## 环境变量配置表

| 环境变量名 | 当前设置值 | 默认值 | 单位 | 说明 | 配置类别 |
|-----------|-----------|--------|------|------|----------|
| **MCP Server 配置** |
| `MCP_ENABLE_CORS` | `true` | `false` | 布尔值 | 启用 CORS 支持 | MCP Server |
| `MCP_SERVER_PORT` | `8775` | `8775` | 端口号 | MCP 服务器端口 | MCP Server |
| **Docker 沙箱配置** |
| `CONTAINER_RUNTIME` | `docker` | `docker` | 字符串 | 容器运行时 (docker/podman) | Docker SDK |
| `LOCALSANDBOX_PYTHON_IMAGE` | `python:3.11-slim` | `python:3.11-slim` | 镜像名 | Python 容器镜像 | Docker SDK |
| `LOCALSANDBOX_NODE_IMAGE` | `node:18-slim` | `node:18-slim` | 镜像名 | Node.js 容器镜像 | Docker SDK |
| `LOCALSANDBOX_DEFAULT_TIMEOUT` | `1800` | `1800` | 秒 | 默认执行超时 (30分钟) | Docker SDK |
| **会话管理配置** |
| `MSB_MAX_SESSIONS` | `5` | `10` | 个数 | 最大并发会话数 | MCP Wrapper |
| `MSB_SESSION_TIMEOUT` | `3600` | `3600` | 秒 | 会话超时时间 (60分钟) | MCP Wrapper |
| `MSB_DEFAULT_FLAVOR` | `small` | `small` | 枚举值 | 默认沙箱规格 | MCP Wrapper |
| `MSB_SESSION_CLEANUP_INTERVAL` | `60` | `60` | 秒 | 会话清理间隔 | MCP Wrapper |
| **Flavor 配置** |
| `MSB_FLAVOR_CONFIGS` | `未设置` | `未设置` | JSON 对象 | 自定义 flavor 配置 | MCP Wrapper |
| **资源限制配置** |
| `MSB_MAX_TOTAL_MEMORY_MB` | `4096` | `null` | MB | 最大总内存限制 | MCP Wrapper |
| `MSB_MAX_EXECUTION_TIME` | `1800` | `1800` | 秒 | 最大执行时间 (30分钟) | MCP Wrapper |
| `MSB_EXECUTION_TIMEOUT` | `1800` | `300` | 秒 | 执行超时 (默认5分钟) | MCP Wrapper |
| **卷映射配置** |
| `MSB_ENABLE_VOLUME_MAPPING` | `true` | `false` | 布尔值 | 启用卷映射 | MCP Wrapper |
| `MSB_SHARED_VOLUME_PATH` | `["/tmp/mcp-sandbox:/workspace"]` | `[]` | JSON 数组 | 共享卷路径映射 | MCP Wrapper |
| **日志配置** |
| `MSB_LOG_LEVEL` | `DEBUG` | `INFO` | 日志级别 | 日志详细程度 | MCP Wrapper |
| `MSB_LOG_FORMAT` | `text` | `json` | 格式 | 日志输出格式 | MCP Wrapper |

## 配置说明

### 🔧 主要配置变更

1. **超时时间调整**：
   - `LOCALSANDBOX_DEFAULT_TIMEOUT`: 从默认的 30 秒增加到 1800 秒 (30分钟)
   - `MSB_SESSION_TIMEOUT`: 从默认的 1800 秒 (30分钟) 增加到 3600 秒 (60分钟)
   - `MSB_EXECUTION_TIMEOUT`: 从默认的 300 秒 (5分钟) 增加到 1800 秒 (30分钟)

2. **会话数限制**：
   - `MSB_MAX_SESSIONS`: 从默认的 10 个减少到 5 个
   - 适合开发环境，减少资源消耗

3. **内存限制**：
   - `MSB_MAX_TOTAL_MEMORY_MB`: 设置为 4096 MB (4GB)
   - 防止过度内存使用

4. **卷映射**：
   - 启用了卷映射功能，映射 `/tmp/mcp-sandbox` 到容器的 `/workspace`
   - 方便文件共享和持久化

5. **配置简化**：
   - 移除了 `LOCALSANDBOX_DEFAULT_MEMORY` 和 `LOCALSANDBOX_DEFAULT_CPU`
   - 这些细粒度配置不再暴露给 MCP 用户，由底层 SDK 管理

### 📊 Flavor 资源配置

| Flavor | 内存限制 | CPU 限制 | 适用场景 |
|--------|----------|----------|----------|
| **small** | 1024 MB | 1.0 核心 | 轻量级任务，简单脚本 |
| **medium** | 2048 MB | 2.0 核心 | 中等工作负载，数据处理 |
| **large** | 4096 MB | 4.0 核心 | 重计算任务，机器学习 |

### 📊 资源配置分析

| 资源类型 | 配置方式 | 总体限制 | 说明 |
|----------|----------|----------|------|
| **内存** | 基于 Flavor | 4096 MB | 通过 flavor 控制单个容器资源 |
| **CPU** | 基于 Flavor | 无限制 | 通过 flavor 控制单个容器资源 |
| **会话** | - | 5 个 | 最多同时运行 5 个沙箱会话 |
| **超时** | 1800 秒 (命令) | 3600 秒 (会话) | 命令级和会话级超时控制 |

### 🐳 Docker 配置

- **运行时**: Docker (也支持 Podman)
- **Python 镜像**: `python:3.11-slim` (约 45MB)
- **Node.js 镜像**: `node:18-slim` (约 110MB)
- **工作目录**: `/workspace`
- **保持运行命令**: `sleep infinity`

### 🔍 监控和日志

- **日志级别**: DEBUG (开发模式，生产环境建议使用 INFO)
- **日志格式**: text (便于阅读，生产环境建议使用 json)
- **清理间隔**: 60 秒检查一次过期会话

### 🎛️ Flavor 自定义配置

可以通过 `MSB_FLAVOR_CONFIGS` 环境变量自定义 flavor 配置：

```bash
# 自定义 flavor 配置示例
MSB_FLAVOR_CONFIGS='{"small": {"memory_mb": 2048, "cpu_limit": 1.5}, "medium": {"memory_mb": 4096, "cpu_limit": 3.0}}'
```

**配置格式**：
- JSON 对象格式
- 每个 flavor 包含 `memory_mb` (整数) 和 `cpu_limit` (浮点数)
- 只需要配置要覆盖的 flavor，其他保持默认值

### ⚠️ 注意事项

1. **配置简化**: 移除了底层的 CPU/内存配置暴露，统一使用 flavor 概念
2. **开发配置**: 当前配置适合开发环境，生产环境可能需要调整资源限制
3. **卷映射路径**: 当前映射到 `/tmp/mcp-sandbox`，重启后可能丢失数据
4. **Flavor 优先级**: 自定义 flavor 配置会覆盖默认配置