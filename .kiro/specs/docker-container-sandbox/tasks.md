# 实现计划

- [x] 1. 创建容器运行时抽象层
  - 实现 ContainerRuntime 基类和相关数据模型
  - 创建 DockerRuntime 具体实现类
  - 实现容器生命周期管理方法（创建、启动、停止、删除）
  - _需求: 1.1, 2.1, 2.2, 9.1, 9.2_

- [x] 1.1 实现容器配置和统计数据模型
  - 创建 ContainerConfig 数据类定义容器配置参数
  - 创建 ContainerStats 数据类定义容器统计信息
  - 实现数据验证和默认值处理
  - _需求: 8.1, 8.2, 8.3_

- [x] 1.2 实现 DockerRuntime 核心命令执行
  - 实现 _run_command 方法执行 Docker CLI 命令
  - 添加超时处理和错误捕获机制
  - 实现命令输出解析和格式化
  - _需求: 1.2, 1.3, 2.3, 4.3_

- [x] 1.3 实现容器管理操作
  - 实现 create_container 方法创建 Docker 容器
  - 实现 start_container、stop_container、remove_container 方法
  - 实现 is_container_running 方法检查容器状态
  - _需求: 9.1, 9.2, 9.3, 9.4_

- [x] 1.4 实现容器内命令执行
  - 实现 execute_command 方法在容器中执行命令
  - 处理命令超时和输出捕获
  - 实现标准输出和错误输出的分离处理
  - _需求: 5.1, 5.2, 5.3_

- [x] 2. 重构 BaseSandbox 类以支持容器运行时
  - 移除 HTTP 客户端相关代码（aiohttp、server_url、api_key）
  - 添加容器运行时配置和初始化
  - 更新 start() 和 stop() 方法使用容器运行时
  - _需求: 1.1, 2.1, 3.1, 9.1, 9.2_

- [x] 2.1 更新 BaseSandbox 构造函数
  - 移除 server_url、api_key、_session 等 HTTP 相关参数
  - 添加 container_runtime 参数支持 Docker/Podman 选择
  - 实现 _create_runtime 方法初始化容器运行时
  - _需求: 2.1, 2.2, 2.3_

- [x] 2.2 重构 sandbox 生命周期管理
  - 更新 start() 方法使用容器运行时创建和启动容器
  - 更新 stop() 方法使用容器运行时停止和清理容器
  - 实现容器 ID 跟踪和状态管理
  - _需求: 9.1, 9.2, 9.3, 9.4_

- [x] 2.3 更新 create() 类方法和上下文管理器
  - 修改 create() 类方法参数，移除 HTTP 相关参数
  - 保持异步上下文管理器接口不变
  - 确保资源清理在异常情况下正确执行
  - _需求: 3.1, 10.1, 10.4_

- [x] 3. 实现 PythonSandbox 容器化执行
  - 更新 get_default_image() 返回 Python Docker 镜像
  - 重构 run() 方法在容器中执行 Python 代码
  - 保持 Execution 对象输出格式兼容性
  - _需求: 3.2, 4.1, 4.2, 7.1, 7.3_

- [x] 3.1 更新 PythonSandbox 镜像配置
  - 实现 get_default_image() 方法返回 Python 容器镜像
  - 支持通过环境变量 LOCALSANDBOX_PYTHON_IMAGE 自定义镜像
  - 添加镜像可用性检查和错误处理
  - _需求: 7.1, 7.3, 7.4_

- [x] 3.2 重构 Python 代码执行逻辑
  - 重写 run() 方法使用容器运行时执行 Python 代码
  - 实现代码注入和异常捕获机制
  - 确保输出格式与原 Execution 对象兼容
  - _需求: 4.1, 4.2, 4.3, 3.2_

- [x] 4. 实现 NodeSandbox 容器化执行
  - 更新 get_default_image() 返回 Node.js Docker 镜像
  - 重构 run() 方法在容器中执行 JavaScript 代码
  - 保持 Execution 对象输出格式兼容性
  - _需求: 3.2, 4.1, 4.2, 7.2, 7.3_

- [x] 4.1 更新 NodeSandbox 镜像配置
  - 实现 get_default_image() 方法返回 Node.js 容器镜像
  - 支持通过环境变量 LOCALSANDBOX_NODE_IMAGE 自定义镜像
  - 添加镜像可用性检查和错误处理
  - _需求: 7.2, 7.3, 7.4_

- [x] 4.2 重构 JavaScript 代码执行逻辑
  - 重写 run() 方法使用容器运行时执行 JavaScript 代码
  - 实现错误捕获和输出处理
  - 确保输出格式与原 Execution 对象兼容
  - _需求: 4.1, 4.2, 4.3, 3.2_

- [x] 5. 重构 Command 类支持容器执行
  - 更新 run() 方法在容器中执行 shell 命令
  - 保持 CommandExecution 对象输出格式兼容性
  - 实现命令参数处理和超时控制
  - _需求: 3.3, 5.1, 5.2, 5.3, 5.4_

- [x] 5.1 重构命令执行逻辑
  - 重写 Command.run() 方法使用容器运行时
  - 实现命令和参数的正确组装
  - 处理命令执行超时和错误情况
  - _需求: 5.1, 5.2, 5.3_

- [x] 5.2 保持 CommandExecution 兼容性
  - 确保 CommandExecution 对象输出格式不变
  - 正确处理退出码、标准输出和错误输出
  - 实现 success 属性的正确计算
  - _需求: 3.3, 5.4_

- [x] 6. 更新 Metrics 类为 TODO 实现
  - 在 BaseSandbox 中将 metrics 属性标记为 TODO
  - 移除或注释现有的 Metrics 类实现
  - 确保调用 metrics 相关方法时返回适当的 TODO 提示
  - _需求: 6.1, 6.2, 6.3_

- [x] 7. 更新项目依赖和配置
  - 更新 pyproject.toml 移除不需要的依赖（如 aiohttp）
  - 添加新的环境变量配置支持
  - 更新项目文档和示例代码
  - _需求: 2.1, 8.4_

- [x] 7.1 更新项目依赖配置
  - 修改 pyproject.toml 移除 aiohttp 和相关 HTTP 依赖
  - 保留必要的异步和工具依赖
  - 更新版本号和项目描述
  - _需求: 2.1_

- [x] 7.2 添加环境变量配置支持
  - 实现容器运行时配置的环境变量读取
  - 添加默认镜像配置的环境变量支持
  - 实现配置验证和错误处理
  - _需求: 2.1, 2.2, 8.4_

- [x] 8. 创建集成测试
  - 编写测试验证容器运行时功能
  - 测试 Python 和 Node.js 代码执行
  - 测试命令执行和错误处理
  - _需求: 1.4, 4.4, 5.4, 10.3_

- [x] 8.1 创建容器运行时测试
  - 测试 DockerRuntime 的基本功能
  - 测试容器创建、启动、停止、删除流程
  - 测试错误情况和异常处理
  - _需求: 1.4, 9.1, 9.2, 9.3_

- [x] 8.2 创建沙箱执行测试
  - 测试 PythonSandbox 和 NodeSandbox 代码执行
  - 测试输出格式兼容性
  - 测试异常情况和错误处理
  - _需求: 4.4, 3.2_

- [x] 8.3 创建命令执行测试
  - 测试 Command 类的 shell 命令执行
  - 测试命令参数处理和超时控制
  - 测试 CommandExecution 对象兼容性
  - _需求: 5.4, 3.3_

- [x] 9. 验证 MCP Server 集成兼容性
  - 确保 microsandbox_wrapper 能正常导入和使用新的 sandbox SDK
  - 测试现有的 MCP server 功能不受影响
  - 验证错误处理和异常传播正确
  - _需求: 3.1, 3.2, 3.3, 10.1_

- [x] 9.1 测试 MCP Server 导入兼容性
  - 验证 session_manager.py 中的 sandbox 导入正常工作
  - 测试 PythonSandbox 和 NodeSandbox 的创建和使用
  - 确保接口兼容性不影响现有功能
  - _需求: 3.1, 3.2_

- [x] 9.2 验证端到端功能
  - 通过 MCP server 测试完整的代码执行流程
  - 测试会话管理和资源清理
  - 验证错误处理和异常传播
  - _需求: 3.3, 10.1, 10.4_