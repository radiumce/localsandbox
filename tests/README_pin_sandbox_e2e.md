# Pin-Sandbox End-to-End Tests

这些测试验证pin-sandbox功能的完整端到端工作流程，使用官方MCP客户端与MCP服务器进行交互。

## 测试概述

### 核心测试流程

1. **创建会话并写入文件** - 在sandbox中创建测试文件
2. **Pin操作** - 使用自定义名称pin sandbox
3. **立即验证** - 确认pin后文件仍然存在
4. **会话清理** - 通过低超时时间触发自动清理
5. **重新附加** - 通过名称重新附加到pinned sandbox
6. **最终验证** - 确认文件在整个周期后仍然存在

### 测试文件

- `test_pin_sandbox_e2e_simple.py` - 简化的端到端测试，专注于核心功能
- `test_pin_sandbox_end_to_end.py` - 完整的端到端测试，包含复杂场景
- `test_config_pin_sandbox.py` - 测试配置和工具函数

## 前置条件

### 1. 安装依赖

```bash
# 安装MCP客户端
pip install mcp

# 安装其他测试依赖
pip install pytest pytest-asyncio
```

### 2. 确保Docker可用

```bash
# 检查Docker是否运行
docker ps

# 如果需要，启动Docker服务
sudo systemctl start docker  # Linux
# 或启动Docker Desktop (macOS/Windows)
```

### 3. 设置MCP服务器

确保MCP服务器代码在正确位置：
```
mcp-server/
├── mcp_server/
│   ├── main.py
│   ├── server.py
│   └── ...
└── requirements.txt
```

## 运行测试

### 方法1: 使用pytest

```bash
# 运行简化的端到端测试
pytest tests/test_pin_sandbox_e2e_simple.py -v

# 运行完整的端到端测试
pytest tests/test_pin_sandbox_end_to_end.py -v

# 运行所有pin-sandbox端到端测试
pytest tests/test_pin_sandbox_e2e*.py -v
```

### 方法2: 直接运行Python脚本

```bash
# 运行简化测试
cd tests
python test_pin_sandbox_e2e_simple.py

# 运行完整测试
python test_pin_sandbox_end_to_end.py
```

### 方法3: 使用环境变量自定义配置

```bash
# 自定义会话超时和清理间隔
SESSION_TIMEOUT=3 CLEANUP_INTERVAL=1 pytest tests/test_pin_sandbox_e2e_simple.py -v

# 启用调试日志
LOG_LEVEL=DEBUG pytest tests/test_pin_sandbox_e2e_simple.py -v -s
```

## 测试配置

### 环境变量

- `SESSION_TIMEOUT` - 会话超时时间（秒），默认8秒
- `CLEANUP_INTERVAL` - 清理检查间隔（秒），默认3秒
- `MAX_CONCURRENT_SESSIONS` - 最大并发会话数，默认5
- `LOG_LEVEL` - 日志级别（DEBUG, INFO, WARNING, ERROR）
- `DOCKER_HOST` - Docker连接地址

### 测试参数

在测试代码中可以调整：

```python
class SimplePinSandboxE2ETest:
    def __init__(self):
        self.session_timeout = 8  # 会话超时
        self.cleanup_interval = 3  # 清理间隔
        self.test_file_path = "/workspace/persistence_test.txt"
        # ...
```

## 测试验证点

### 1. 文件持久性验证

- ✅ 文件在pin操作后立即存在
- ✅ 文件内容正确且完整
- ✅ 文件在会话清理后仍然存在
- ✅ 文件在重新附加后仍然可访问

### 2. 会话管理验证

- ✅ Pin操作成功返回确认消息
- ✅ 原始会话在超时后被清理
- ✅ 重新附加操作成功
- ✅ 新会话ID与原始会话ID不同

### 3. 容器状态验证

- ✅ Pinned容器在清理时被保留
- ✅ 容器可以从停止状态重新启动
- ✅ 容器标签正确设置
- ✅ 容器数据完整保留

## 故障排除

### 常见问题

1. **MCP客户端不可用**
   ```
   ImportError: No module named 'mcp'
   ```
   解决：`pip install mcp`

2. **Docker连接失败**
   ```
   Error: Cannot connect to Docker daemon
   ```
   解决：确保Docker服务运行，检查DOCKER_HOST环境变量

3. **MCP服务器启动失败**
   ```
   FileNotFoundError: MCP server script not found
   ```
   解决：检查mcp-server目录结构，确保main.py存在

4. **测试超时**
   ```
   asyncio.TimeoutError
   ```
   解决：增加TEST_TIMEOUT值或检查Docker性能

### 调试技巧

1. **启用详细日志**
   ```bash
   LOG_LEVEL=DEBUG pytest tests/test_pin_sandbox_e2e_simple.py -v -s
   ```

2. **检查Docker容器**
   ```bash
   # 查看运行中的容器
   docker ps
   
   # 查看所有容器（包括停止的）
   docker ps -a
   
   # 查看pinned容器
   docker ps -a --filter "label=pinned=true"
   ```

3. **手动测试MCP工具**
   ```bash
   # 启动MCP服务器
   cd mcp-server
   python -m mcp_server.main
   
   # 在另一个终端使用MCP客户端测试
   ```

## 测试结果解读

### 成功输出示例

```
🚀 Starting Pin-Sandbox End-to-End Test
==================================================
🔧 Setting up MCP server for test ID: abc12345
✅ MCP server started (PID: 12345)
📝 Step 1: Creating session and writing test file
   Session ID: session-def67890
📌 Step 2: Pinning sandbox as 'test_pinned_abc12345'
   ✅ Sandbox pinned successfully
🔍 Step 2.5: Verifying file persistence
   ✅ File exists: /workspace/persistence_test.txt
   ✅ Content matches: True
⏳ Step 3: Waiting 13s for session cleanup
   ✅ Cleanup wait period completed
🔗 Step 4: Attaching to pinned sandbox 'test_pinned_abc12345'
   ✅ Attached successfully. New session: session-ghi09876
🔍 Step 5: Verifying file persistence
   ✅ File exists: /workspace/persistence_test.txt
   ✅ Content matches: True
==================================================
🎉 PIN-SANDBOX TEST PASSED!
✅ File persisted through pin → cleanup → attach cycle
✅ Sandbox state continuity verified
==================================================
```

### 失败输出示例

```
❌ TEST FAILED: File missing after cleanup and reattachment
```

## 扩展测试

### 添加新的测试场景

1. **复制现有测试类**
2. **修改测试逻辑**
3. **添加新的验证点**

示例：
```python
class CustomPinSandboxTest(SimplePinSandboxE2ETest):
    async def create_custom_files(self):
        # 自定义文件创建逻辑
        pass
    
    async def verify_custom_persistence(self):
        # 自定义验证逻辑
        pass
```

### 性能测试

可以扩展测试来验证：
- 大文件持久性
- 多个pinned sandbox并发操作
- 长时间运行的容器状态
- 资源使用情况

## 贡献

如果需要添加新的测试场景或改进现有测试：

1. 遵循现有的测试结构
2. 添加适当的错误处理
3. 包含详细的日志输出
4. 更新此README文档