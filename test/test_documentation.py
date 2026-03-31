"""
YourWork - 测试框架说明
创建统一的测试说明文档
"""

# 测试框架说明文档
TEST_DOCUMENTATION = """
# YourWork 测试用例说明

## 测试架构概述

测试框架分为三个层次：

```
test/
├── test_base.py              # 测试基础设施
├── test_data_generator.py    # 测试数据生成器
├── test_config.py           # 测试配置
├── test_runner.py           # 测试运行器
│
├── unit/                    # 单元测试
│   ├── test_utils.py        # 工具函数测试
│   ├── test_database.py     # 数据库操作测试
│   └── test_auth_module.py  # 认证模块测试
│
├── integration/             # 集成测试
│   ├── test_auth_flow.py    # 认证流程测试
│   ├── test_project_flow.py # 项目管理流程测试
│   └── test_milestone_flow.py # 里程碑管理流程测试
│
└── system/                  # 系统测试
    ├── test_end_to_end.py   # 端到端测试
    └── test_scenarios.py    # 场景测试
```

## 测试分类说明

### 1. 单元测试 (Unit Tests)

**目的**: 测试单个函数、类或组件的正确性

**覆盖范围**:
- `test_utils.py`: 测试工具函数
  - ID 生成 (`generate_id`)
  - 密码哈希 (`hash_password`, `verify_password`)
  - 数据库辅助函数
  - 日志函数
  - 权限检查函数

- `test_database.py`: 测试数据库 CRUD 操作
  - 用户增删改查
  - 项目增删改查
  - 里程碑增删改查
  - 项目成员操作
  - 消息操作

- `test_auth_module.py`: 测试认证模块
  - 登录 API
  - 登出 API
  - 获取用户信息 API
  - 注册 API
  - 安全性测试

**运行方式**:
```bash
python test/test_runner.py --type unit
```

### 2. 集成测试 (Integration Tests)

**目的**: 测试多个模块之间的交互

**覆盖范围**:
- `test_auth_flow.py`: 认证流程测试
  - 注册 -> 登录 -> 登出完整流程
  - 角色权限验证
  - 会话管理
  - 并发登录

- `test_project_flow.py`: 项目管理流程测试
  - 项目 CRUD 流程
  - 项目分页和搜索
  - 项目成员管理
  - 成员权限控制
  - 项目与里程碑集成

- `test_milestone_flow.py`: 里程碑管理流程测试
  - 里程碑完整生命周期
  - 里程碑状态转换
  - 操作日志记录
  - 里程碑与产出物集成
  - 父子里程碑关系

**运行方式**:
```bash
python test/test_runner.py --type integration
```

### 3. 系统测试 (System Tests)

**目的**: 测试完整的业务流程和用户场景

**覆盖范围**:
- `test_end_to_end.py`: 端到端测试
  - 项目从创建到完成的完整生命周期
  - 新用户入职流程
  - 多项目管理流程
  - 团队协作流程
  - 项目交接流程

- `test_scenarios.py`: 场景测试
  - 错误恢复场景
  - 并发操作场景
  - 数据完整性场景
  - 性能场景
  - 边界值场景
  - 安全场景

**运行方式**:
```bash
python test/test_runner.py --type system
```

## 测试用例统计

### 单元测试用例 (约 50+ 个)

| 模块 | 测试类 | 用例数 |
|------|--------|--------|
| 工具函数 | TestGenerateId | 4 |
|  | TestHashPassword | 7 |
|  | TestVerifyPassword | 5 |
|  | TestDatabaseHelpers | 5 |
|  | TestLogFunctions | 2 |
|  | TestPermissionCheck | 3 |
|  | TestDateTimeUtils | 3 |
| 数据库 | TestUserDatabaseOperations | 6 |
|  | TestProjectDatabaseOperations | 6 |
|  | TestMilestoneDatabaseOperations | 6 |
|  | TestProjectMemberOperations | 5 |
|  | TestMessageOperations | 5 |
| 认证 | TestAuthLoginAPI | 9 |
|  | TestAuthLogoutAPI | 3 |
|  | TestAuthProfileAPI | 5 |
|  | TestAuthRegisterAPI | 5 |
|  | TestAuthSecurity | 4 |

### 集成测试用例 (约 40+ 个)

| 模块 | 测试类 | 用例数 |
|------|--------|--------|
| 认证流程 | TestCompleteAuthFlow | 5 |
|  | TestRoleBasedAccessFlow | 4 |
|  | TestSessionManagement | 3 |
|  | TestPasswordRecoveryFlow | 2 |
| 项目流程 | TestProjectLifecycleFlow | 3 |
|  | TestProjectMemberFlow | 3 |
|  | TestProjectWithMilestonesFlow | 2 |
|  | TestProjectDeliverablesFlow | 2 |
| 里程碑流程 | TestMilestoneLifecycleFlow | 3 |
|  | TestMilestoneLogsFlow | 3 |
|  | TestMilestoneWithDeliverablesFlow | 2 |
|  | TestMilestoneParentChildFlow | 2 |

### 系统测试用例 (约 30+ 个)

| 模块 | 测试类 | 用例数 |
|------|--------|--------|
| 端到端 | TestCompleteProjectLifecycle | 1 (8步骤) |
|  | TestNewUserOnboardingFlow | 1 (5步骤) |
|  | TestMultiProjectManagementFlow | 1 (4步骤) |
|  | TestProjectCollaborationFlow | 1 (6步骤) |
|  | TestProjectHandoverFlow | 1 (4步骤) |
| 场景 | TestErrorRecoveryScenarios | 3 |
|  | TestConcurrentOperationsScenarios | 3 |
|  | TestDataIntegrityScenarios | 3 |
|  | TestPerformanceScenarios | 3 |
|  | TestBoundaryScenarios | 5 |
|  | TestSecurityScenarios | 4 |

**总计**: 约 120+ 个测试用例

## 运行所有测试

```bash
# 运行所有类型的测试
python test/test_runner.py --type all

# 运行特定测试
python test/test_runner.py --type specific --test test.unit.test_utils

# 生成测试报告
python test/test_runner.py --type all --report

# 详细输出
python test/test_runner.py --type all --verbose
```

## 测试覆盖率

目标测试覆盖率：
- 代码行覆盖率: ≥ 80%
- 分支覆盖率: ≥ 70%
- 函数覆盖率: ≥ 85%

## 测试最佳实践

1. **独立性**: 每个测试用例应该独立运行，不依赖其他测试
2. **可重复性**: 测试应该可以多次运行并产生相同结果
3. **清晰性**: 测试名称和断言应该清晰表达测试意图
4. **完整性**: 测试应该覆盖正常流程和边界情况
5. **性能**: 测试本身应该快速执行

## 测试数据管理

- 测试使用独立的测试数据库
- 每个测试类前后自动清理数据
- 使用 `TestDataGenerator` 生成一致的测试数据
- 敏感数据使用假数据，不使用真实用户信息

## 持续集成

测试框架设计为可集成到 CI/CD 流程：

```yaml
# .github/workflows/test.yml 示例
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python test/test_runner.py --type all --report
```

## 问题排查

### 测试失败时的排查步骤

1. 查看详细错误信息
   ```bash
   python test/test_runner.py --type unit --verbose
   ```

2. 运行特定失败的测试
   ```bash
   python -m unittest test.unit.test_utils.TestGenerateId.test_generate_id_returns_string
   ```

3. 检查测试数据库状态
   ```bash
   # 测试数据库位置
   ls test/test_*.db
   ```

4. 清理并重新运行
   ```bash
   rm -f test/test_*.db
   python test/test_runner.py --type all
   ```

## 贡献指南

添加新测试时：

1. 确定测试类型（单元/集成/系统）
2. 在对应目录创建测试文件
3. 继承合适的基类（`APITestBase`, `DatabaseTestBase`）
4. 编写测试用例，遵循命名规范 `test_*`
5. 在文档中更新测试用例统计
6. 运行测试确保通过
"""


def print_documentation():
    """打印测试框架文档"""
    print(TEST_DOCUMENTATION)


if __name__ == "__main__":
    print_documentation()
