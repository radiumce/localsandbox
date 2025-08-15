# 配置修复总结

## 修复的问题

### ✅ 问题1: Flavor 设计优化
**问题**: 不应该暴露 `LOCALSANDBOX_DEFAULT_MEMORY` 和 `LOCALSANDBOX_DEFAULT_CPU` 给 MCP 用户
**解决方案**: 
- 移除了这些配置从 `.env.docker` 文件
- 保持底层 python/sandbox 的细粒度控制能力
- MCP server 层面只暴露 flavor 概念
- 添加了 JSON 格式的 flavor 自定义配置支持

### ✅ 问题2: 超时时间修复
**问题**: `LOCALSANDBOX_DEFAULT_TIMEOUT` 默认 30s 太短
**解决方案**: 
- 修改默认值从 30s → 1800s (30分钟)
- 更新了 python/sandbox/config.py 中的默认值

### ✅ 问题3: 会话超时修复  
**问题**: `MSB_SESSION_TIMEOUT` 默认应该是 3600s
**解决方案**:
- 修改默认值从 1800s → 3600s (60分钟)
- 更新了 mcp-server/wrapper/config.py

### ✅ 问题4: 清理已弃用配置
**问题**: 已弃用的配置应该清理掉
**解决方案**:
- 从 `.env.docker` 移除了 `MSB_SERVER_URL` 和 `MSB_API_KEY`
- 移除了 `LOCALSANDBOX_DEFAULT_MEMORY` 和 `LOCALSANDBOX_DEFAULT_CPU`

## 新增功能

### 🎛️ JSON 格式的 Flavor 配置
添加了 `MSB_FLAVOR_CONFIGS` 环境变量支持：

```bash
MSB_FLAVOR_CONFIGS='{"small": {"memory_mb": 2048, "cpu_limit": 1.5}}'
```

**特性**:
- JSON 对象格式，支持自定义任意 flavor
- 只需配置要覆盖的 flavor，其他保持默认
- 动态覆盖 SandboxFlavor 枚举的方法
- 完整的配置验证和错误处理

## 验证结果

所有修复都通过了自动化测试验证：
- ✅ 超时配置修复验证
- ✅ MCP 会话超时修复验证  
- ✅ JSON flavor 配置功能验证
- ✅ 已弃用配置清理验证

## 配置架构

现在的配置架构更加清晰：
- **底层 (python/sandbox)**: 保持细粒度的 CPU/内存控制
- **上层 (MCP server)**: 只暴露 flavor 概念给用户
- **自定义**: 通过 JSON 配置灵活覆盖 flavor 设置