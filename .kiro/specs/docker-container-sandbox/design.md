# 设计文档

## 概述

本设计文档描述了如何将 localsandbox 项目中的 Python sandbox SDK 从基于 microsandbox 服务器的实现改为基于 Docker 容器的本地实现。设计的核心目标是保持现有 API 接口不变，同时将底层实现从 HTTP 请求改为直接的 Docker 命令行调用。

## 架构

### 高层架构

```
MCP Server (microsandbox_wrapper)
    ↓ (导入使用)
Python Sandbox SDK (python/sandbox)
    ↓ (新的实现)
Docker Container Runtime
    ↓
Local Docker Daemon
```

### 核心变更

1. **移除 HTTP 客户端依赖**：不再使用 `aiohttp` 与远程服务器通信
2. **引入容器运行时抽象**：支持 Docker 和 Podman
3. **本地容器管理**：直接管理本地容器的生命周期
4. **保持接口兼容性**：所有公共 API 保持不变

## 组件和接口

### 1. 容器运行时抽象层

#### ContainerRuntime 基类

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class ContainerConfig:
    """容器配置"""
    image: str
    name: str
    memory: Optional[int] = None  # MB
    cpus: Optional[float] = None
    volumes: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None
    working_dir: str = "/workspace"
    command: Optional[List[str]] = None

@dataclass
class ContainerStats:
    """容器统计信息"""
    cpu_percent: Optional[float] = None
    memory_usage_mb: Optional[int] = None
    memory_limit_mb: Optional[int] = None
    is_running: bool = False

class ContainerRuntime(ABC):
    """容器运行时抽象基类"""
    
    @abstractmethod
    async def create_container(self, config: ContainerConfig) -> str:
        """创建容器，返回容器ID"""
        pass
    
    @abstractmethod
    async def start_container(self, container_id: str) -> None:
        """启动容器"""
        pass
    
    @abstractmethod
    async def stop_container(self, container_id: str) -> None:
        """停止容器"""
        pass
    
    @abstractmethod
    async def remove_container(self, container_id: str) -> None:
        """删除容器"""
        pass
    
    @abstractmethod
    async def execute_command(
        self, 
        container_id: str, 
        command: List[str],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """在容器中执行命令"""
        pass
    
    @abstractmethod
    async def get_container_stats(self, container_id: str) -> ContainerStats:
        """获取容器统计信息"""
        pass
    
    @abstractmethod
    async def is_container_running(self, container_id: str) -> bool:
        """检查容器是否运行"""
        pass
```

#### DockerRuntime 实现

```python
import asyncio
import json
import subprocess
from typing import List, Optional, Dict, Any

class DockerRuntime(ContainerRuntime):
    """Docker 容器运行时实现"""
    
    def __init__(self, docker_cmd: str = "docker"):
        self.docker_cmd = docker_cmd
    
    async def _run_command(self, args: List[str], timeout: Optional[int] = None) -> Dict[str, Any]:
        """执行 Docker 命令"""
        cmd = [self.docker_cmd] + args
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            return {
                "returncode": process.returncode,
                "stdout": stdout.decode('utf-8'),
                "stderr": stderr.decode('utf-8')
            }
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise RuntimeError(f"Command timed out: {' '.join(cmd)}")
        except Exception as e:
            raise RuntimeError(f"Failed to execute command {' '.join(cmd)}: {e}")
```

### 2. 更新的 BaseSandbox 类

#### 核心变更

```python
class BaseSandbox(ABC):
    """基础沙箱类 - 基于容器的实现"""
    
    def __init__(
        self,
        container_runtime: Optional[str] = None,
        namespace: str = "default",
        name: Optional[str] = None,
        **kwargs
    ):
        # 移除 server_url, api_key 等 HTTP 相关参数
        # 添加容器运行时配置
        self._container_runtime_name = container_runtime or os.environ.get("CONTAINER_RUNTIME", "docker")
        self._namespace = namespace
        self._name = name or f"sandbox-{uuid.uuid4().hex[:8]}"
        self._container_id: Optional[str] = None
        self._is_started = False
        
        # 初始化容器运行时
        self._runtime = self._create_runtime()
    
    def _create_runtime(self) -> ContainerRuntime:
        """创建容器运行时实例"""
        if self._container_runtime_name.lower() == "docker":
            return DockerRuntime("docker")
        elif self._container_runtime_name.lower() == "podman":
            return DockerRuntime("podman")  # Podman 兼容 Docker CLI
        else:
            raise ValueError(f"Unsupported container runtime: {self._container_runtime_name}")
    
    async def start(
        self,
        image: Optional[str] = None,
        memory: int = 512,
        cpus: float = 1.0,
        timeout: float = 180.0,
        volumes: Optional[list] = None,
    ) -> None:
        """启动沙箱容器"""
        if self._is_started:
            return
        
        sandbox_image = image or await self.get_default_image()
        
        # 构建容器配置
        config = ContainerConfig(
            image=sandbox_image,
            name=self._name,
            memory=memory,
            cpus=cpus,
            volumes=volumes or [],
            working_dir="/workspace"
        )
        
        try:
            # 创建并启动容器
            self._container_id = await self._runtime.create_container(config)
            await self._runtime.start_container(self._container_id)
            self._is_started = True
        except Exception as e:
            raise RuntimeError(f"Failed to start sandbox: {e}")
    
    async def stop(self) -> None:
        """停止沙箱容器"""
        if not self._is_started or not self._container_id:
            return
        
        try:
            await self._runtime.stop_container(self._container_id)
            await self._runtime.remove_container(self._container_id)
            self._is_started = False
            self._container_id = None
        except Exception as e:
            raise RuntimeError(f"Failed to stop sandbox: {e}")
```

### 3. 语言特定的沙箱实现

#### PythonSandbox 更新

```python
class PythonSandbox(BaseSandbox):
    """Python 沙箱实现"""
    
    async def get_default_image(self) -> str:
        """获取默认的 Python Docker 镜像"""
        return os.environ.get("LOCALSANDBOX_PYTHON_IMAGE", "python:3.11-slim")
    
    async def run(self, code: str) -> Execution:
        """在容器中执行 Python 代码"""
        if not self._is_started:
            raise RuntimeError("Sandbox is not started. Call start() first.")
        
        # 创建临时 Python 脚本
        script_content = f"""
import sys
import traceback
import json

try:
    # 执行用户代码
    exec('''{code}''')
except Exception as e:
    # 捕获异常并输出到 stderr
    traceback.print_exc()
    sys.exit(1)
"""
        
        # 在容器中执行 Python 代码
        command = ["python", "-c", script_content]
        
        try:
            result = await self._runtime.execute_command(
                self._container_id,
                command,
                timeout=30
            )
            
            # 构建输出数据
            output_data = {
                "output": [],
                "status": "success" if result["returncode"] == 0 else "error",
                "language": "python"
            }
            
            # 添加 stdout 输出
            if result["stdout"]:
                for line in result["stdout"].splitlines():
                    output_data["output"].append({
                        "stream": "stdout",
                        "text": line
                    })
            
            # 添加 stderr 输出
            if result["stderr"]:
                for line in result["stderr"].splitlines():
                    output_data["output"].append({
                        "stream": "stderr", 
                        "text": line
                    })
            
            return Execution(output_data=output_data)
            
        except Exception as e:
            raise RuntimeError(f"Failed to execute code: {e}")
```

#### NodeSandbox 更新

```python
class NodeSandbox(BaseSandbox):
    """Node.js 沙箱实现"""
    
    async def get_default_image(self) -> str:
        """获取默认的 Node.js Docker 镜像"""
        return os.environ.get("LOCALSANDBOX_NODE_IMAGE", "node:18-slim")
    
    async def run(self, code: str) -> Execution:
        """在容器中执行 JavaScript 代码"""
        if not self._is_started:
            raise RuntimeError("Sandbox is not started. Call start() first.")
        
        # 在容器中执行 Node.js 代码
        command = ["node", "-e", code]
        
        try:
            result = await self._runtime.execute_command(
                self._container_id,
                command,
                timeout=30
            )
            
            # 构建输出数据（与 PythonSandbox 类似）
            output_data = {
                "output": [],
                "status": "success" if result["returncode"] == 0 else "error",
                "language": "nodejs"
            }
            
            # 处理输出...
            
            return Execution(output_data=output_data)
            
        except Exception as e:
            raise RuntimeError(f"Failed to execute code: {e}")
```

### 4. Command 类更新

```python
class Command:
    """命令执行类 - 基于容器的实现"""
    
    def __init__(self, sandbox_instance):
        self._sandbox = sandbox_instance
    
    async def run(
        self,
        command: str,
        args: Optional[List[str]] = None,
        timeout: Optional[int] = None,
    ) -> CommandExecution:
        """在容器中执行 shell 命令"""
        if not self._sandbox._is_started:
            raise RuntimeError("Sandbox is not started. Call start() first.")
        
        # 构建完整命令
        full_command = [command]
        if args:
            full_command.extend(args)
        
        try:
            result = await self._sandbox._runtime.execute_command(
                self._sandbox._container_id,
                full_command,
                timeout=timeout
            )
            
            # 构建输出数据
            output_data = {
                "output": [],
                "command": command,
                "args": args or [],
                "exit_code": result["returncode"],
                "success": result["returncode"] == 0
            }
            
            # 处理输出...
            
            return CommandExecution(output_data=output_data)
            
        except Exception as e:
            raise RuntimeError(f"Failed to execute command: {e}")
```

## 数据模型

### 保持现有模型不变

- `Execution` 类保持不变
- `CommandExecution` 类保持不变
- 输出格式保持与原实现兼容

### 新增配置模型

```python
@dataclass
class ContainerRuntimeConfig:
    """容器运行时配置"""
    runtime_type: str = "docker"  # docker 或 podman
    default_python_image: str = "python:3.11-slim"
    default_node_image: str = "node:18-slim"
    default_memory_mb: int = 512
    default_cpu_limit: float = 1.0
    default_timeout: int = 30
```

## 错误处理

### 错误类型映射

| 原错误场景 | 新错误场景 | 处理方式 |
|-----------|-----------|----------|
| HTTP 连接失败 | Docker 命令执行失败 | 抛出 `RuntimeError` |
| 服务器返回错误 | 容器创建/启动失败 | 抛出 `RuntimeError` |
| 认证失败 | 容器运行时不可用 | 抛出 `RuntimeError` |
| 超时 | 命令执行超时 | 抛出 `TimeoutError` |

### 错误处理策略

1. **容器运行时检查**：启动时验证 Docker/Podman 是否可用
2. **镜像可用性检查**：自动拉取不存在的镜像
3. **资源清理**：确保异常情况下容器被正确清理
4. **详细错误信息**：提供具体的错误原因和建议

## 测试策略

### 单元测试

1. **容器运行时测试**：测试 Docker/Podman 命令执行
2. **沙箱生命周期测试**：测试创建、启动、停止、清理
3. **代码执行测试**：测试 Python/Node.js 代码执行
4. **命令执行测试**：测试 shell 命令执行
5. **错误处理测试**：测试各种异常情况

### 集成测试

1. **MCP Server 集成**：确保与现有 MCP server 兼容
2. **并发执行测试**：测试多个沙箱并发运行
3. **资源限制测试**：测试内存和 CPU 限制
4. **卷映射测试**：测试文件系统挂载

### 兼容性测试

1. **API 兼容性**：确保所有公共接口保持不变
2. **输出格式兼容性**：确保输出格式与原实现一致
3. **错误兼容性**：确保错误类型和消息格式兼容

## 配置管理

### 环境变量

```bash
# 容器运行时配置
CONTAINER_RUNTIME=docker  # 或 podman
LOCALSANDBOX_PYTHON_IMAGE=python:3.11-slim
LOCALSANDBOX_NODE_IMAGE=node:18-slim

# 默认资源限制
LOCALSANDBOX_DEFAULT_MEMORY=512
LOCALSANDBOX_DEFAULT_CPU=1.0
LOCALSANDBOX_DEFAULT_TIMEOUT=30
```

### 配置文件支持

支持通过配置文件指定容器运行时和镜像配置，与现有的 MCP server 配置集成。

## 部署考虑

### 依赖变更

1. **移除依赖**：`aiohttp`、`python-dotenv`（如果不再需要）
2. **系统依赖**：Docker 或 Podman 必须安装并可用
3. **镜像依赖**：需要预先拉取或配置镜像拉取策略

### 向后兼容性

1. **API 兼容**：所有公共 API 保持不变
2. **配置兼容**：现有配置参数被忽略但不报错
3. **渐进迁移**：支持配置开关在新旧实现间切换（可选）

## 性能考虑

### 优化策略

1. **容器复用**：避免频繁创建/销毁容器
2. **镜像缓存**：预拉取常用镜像
3. **并发控制**：限制同时运行的容器数量
4. **资源监控**：监控容器资源使用情况

### 性能指标

- 容器启动时间：目标 < 2 秒
- 代码执行延迟：目标 < 100ms 额外开销
- 内存使用：每个容器 < 512MB 默认限制
- 并发能力：支持至少 10 个并发容器