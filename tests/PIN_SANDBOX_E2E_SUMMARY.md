# Pin-Sandbox 端到端测试套件总结

## 概述

我已经创建了一个完整的端到端测试套件来验证pin-sandbox功能，使用官方MCP客户端与MCP服务器进行交互。这个测试套件完全符合你的要求：

1. ✅ **使用官方MCP客户端** - 使用`mcp`包的官方客户端
2. ✅ **验证文件持久性** - 在pin操作后立即验证文件存在
3. ✅ **真实会话清理** - 通过环境变量设置低超时时间触发自动清理
4. ✅ **完整工作流程** - pin → 验证 → 清理 → attach → 再次验证

## 测试文件结构

```
tests/
├── test_pin_sandbox_e2e_simple.py      # 简化的端到端测试（推荐开始）
├── test_pin_sandbox_end_to_end.py      # 完整的端到端测试
├── test_config_pin_sandbox.py          # 测试配置和工具函数
├── run_pin_sandbox_e2e.py              # 测试运行器脚本
├── verify_mcp_server.py                # MCP服务器验证脚本
├── README_pin_sandbox_e2e.md           # 详细使用说明
└── PIN_SANDBOX_E2E_SUMMARY.md          # 本总结文档
```

## 核心测试流程

### 1. 简化测试 (`test_pin_sandbox_e2e_simple.py`)

这是推荐的起始测试，专注于核心功能：

```python
async def run_test(self):
    # Step 1: 创建会话并写入测试文件
    session_id = await self.create_session_and_write_file()
    
    # Step 2: Pin sandbox
    await self.pin_sandbox(session_id)
    
    # Step 2.5: 立即验证文件存在
    file_exists = await self.verify_file_exists(session_id, "After Pin")
    assert file_exists, "文件在pin后应该存在"
    
    # Step 3: 等待会话清理（通过低超时时间）
    await self.wait_for_cleanup()
    
    # Step 4: 重新attach到pinned sandbox
    new_session_id = await self.attach_to_pinned_sandbox()
    
    # Step 5: 验证文件仍然存在
    file_still_exists = await self.verify_file_exists(new_session_id, "After Attach")
    assert file_still_exists, "文件在清理和重新attach后应该仍然存在"
```

### 2. 配置特点

- **会话超时**: 8秒（可配置）
- **清理间隔**: 3秒（可配置）
- **测试文件**: `/workspace/persistence_test.txt`
- **自动清理**: 通过环境变量触发，无需模拟

### 3. 验证点

✅ **Pin操作后立即验证**:
```python
# 在pin操作后立即检查文件
file_exists_after_pin = await self.verify_file_exists(session_id, "Step 2.5")
if not file_exists_after_pin:
    raise AssertionError("File missing immediately after pin operation")
```

✅ **会话清理验证**:
```python
# 等待超时时间 + 清理间隔 + 缓冲时间
cleanup_wait = self.session_timeout + self.cleanup_interval + 2
await asyncio.sleep(cleanup_wait)
```

✅ **重新attach后验证**:
```python
# 验证文件在整个周期后仍然存在
file_exists_after_attach = await self.verify_file_exists(new_session_id, "Step 5")
if not file_exists_after_attach:
    raise AssertionError("File missing after cleanup and reattachment")
```

## 快速开始

### 1. 安装依赖
```bash
pip install mcp pytest pytest-asyncio
```

### 2. 验证MCP服务器
```bash
python tests/verify_mcp_server.py
```

### 3. 运行简化测试
```bash
python tests/run_pin_sandbox_e2e.py --simple
```

### 4. 运行所有测试
```bash
python tests/run_pin_sandbox_e2e.py --all
```

## 测试配置选项

### 环境变量配置
```bash
# 更快的清理周期（用于快速测试）
SESSION_TIMEOUT=5 CLEANUP_INTERVAL=2 python tests/run_pin_sandbox_e2e.py --simple

# 调试模式
LOG_LEVEL=DEBUG python tests/run_pin_sandbox_e2e.py --simple --debug
```

### 命令行选项
```bash
# 自定义超时时间
python tests/run_pin_sandbox_e2e.py --timeout=5 --cleanup=2

# 干运行（查看会执行什么）
python tests/run_pin_sandbox_e2e.py --dry-run

# 直接运行（不使用pytest）
python tests/run_pin_sandbox_e2e.py --direct
```

## 测试验证的需求

根据`.kiro/specs/pin-sandbox-feature/requirements.md`，测试验证了以下需求：

### Requirement 1: Pin sandbox with custom name
- ✅ 测试pin_sandbox工具调用
- ✅ 验证自定义名称设置
- ✅ 验证pin操作成功消息

### Requirement 2: Pinned sandboxes survive session cleanup
- ✅ 通过低SESSION_TIMEOUT触发真实清理
- ✅ 验证容器被保留（通过成功的重新attach）
- ✅ 验证数据持久性（文件仍然存在）

### Requirement 4: Attach to pinned sandbox by name
- ✅ 测试attach_sandbox_by_name工具调用
- ✅ 验证通过名称成功重新连接
- ✅ 验证新session_id生成

### Requirement 6: Proper error handling
- ✅ 测试各种错误场景
- ✅ 验证错误消息格式

## 高级测试场景

### 1. 多文件持久性测试
```python
# test_pin_sandbox_e2e_simple.py 中的 test_pin_sandbox_with_multiple_files
- 创建多种类型文件（文本、JSON、Python脚本、日志）
- 验证所有文件类型都能持久化
- 测试Python脚本在重新attach后仍可执行
```

### 2. 复杂文件结构测试
```python
# test_pin_sandbox_end_to_end.py 中的高级场景
- 嵌套目录结构
- 二进制文件（pickle）
- 大文件内容
- 并发操作
```

## 故障排除

### 常见问题及解决方案

1. **MCP客户端不可用**
   ```bash
   pip install mcp
   ```

2. **Docker连接问题**
   ```bash
   docker ps  # 确保Docker运行
   export DOCKER_HOST=unix:///var/run/docker.sock
   ```

3. **测试超时**
   ```bash
   # 增加超时时间
   python tests/run_pin_sandbox_e2e.py --timeout=15 --cleanup=5
   ```

4. **服务器启动失败**
   ```bash
   # 验证服务器
   python tests/verify_mcp_server.py
   ```

## 测试输出示例

### 成功运行示例
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

## 与现有测试的关系

这个端到端测试套件补充了现有的单元测试和集成测试：

- **单元测试** (`test_pin_sandbox_functionality.py`) - 测试个别组件
- **集成测试** (`test_pin_sandbox_integration.py`) - 测试组件交互
- **端到端测试** (本套件) - 测试完整用户工作流程

## 总结

这个端到端测试套件提供了：

1. **真实环境测试** - 使用真实的MCP客户端和服务器
2. **完整工作流程验证** - 从创建到pin到清理到重新attach
3. **状态持久性验证** - 确保文件和数据在整个周期中保持不变
4. **灵活配置** - 可调整超时时间和清理间隔
5. **详细日志** - 每个步骤都有清晰的输出
6. **错误处理** - 适当的错误检测和报告

这个测试套件完全满足了你的要求，提供了一个可靠的方式来验证pin-sandbox功能的端到端正确性。