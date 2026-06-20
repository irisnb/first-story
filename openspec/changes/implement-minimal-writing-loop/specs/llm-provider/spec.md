## ADDED Requirements

### Requirement: 多模型 provider 抽象
系统 SHALL 提供统一的 LLM 接口层，封装多家 provider（如 OpenAI / Claude / 国产模型），使提取等能力依赖抽象而非具体 SDK。

#### Scenario: 提取依赖抽象接口
- **WHEN** 提取能力需要调用 LLM
- **THEN** 它通过统一接口层发起调用，不直接绑定任何单一 provider 的 SDK

#### Scenario: 切换 provider 不改提取逻辑
- **WHEN** 配置从一个 provider 切换到另一个
- **THEN** 提取等上层能力无需修改代码即可工作

### Requirement: API key 与模型配置
系统 SHALL 从环境变量读取 API key 与模型选择，API key MUST NOT 入库、回显或写入日志。

#### Scenario: 从环境变量读取配置
- **WHEN** 系统启动并需要调用 LLM
- **THEN** 系统从环境变量读取 API key 与模型名，未配置时给出明确提示而非崩溃

#### Scenario: key 不泄露
- **WHEN** 系统记录日志或向前端返回数据
- **THEN** API key 的值不出现在日志、响应或任何持久化存储中

#### Scenario: 外部调用走代理
- **WHEN** 系统向外部 LLM 服务发起请求
- **THEN** 请求通过配置的代理发出

### Requirement: token 用量追踪
系统 SHALL 记录每次 LLM 调用的 token 用量。

#### Scenario: 记录调用用量
- **WHEN** 一次 LLM 调用完成
- **THEN** 系统记录该次调用的输入/输出 token 数，供后续成本观测
