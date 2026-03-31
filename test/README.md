# YourWork 测试说明

## 测试目录结构

```
test/
├── test_api.py          # API 接口测试
├── test_db.py           # 数据库操作测试
├── test_data/           # 测试数据目录
│   ├── sample.xlsx      # 示例 Excel 文件
│   └── sample.pdf       # 示例 PDF 文件
└── README.md            # 本文件
```

## 运行测试

### 运行所有测试

```bash
# 运行 API 测试
python test/test_api.py

# 运行数据库测试
python test/test_db.py
```

### 使用 pytest 运行（可选）

如果安装了 pytest：

```bash
# 安装 pytest
pip install pytest

# 运行所有测试
pytest test/

# 运行特定测试文件
pytest test/test_api.py

# 显示详细输出
pytest test/ -v

# 显示测试覆盖率（需要安装 pytest-cov）
pip install pytest-cov
pytest test/ --cov=. --cov-report=html
```

## 测试说明

### API 测试 (test_api.py)

测试所有 API 端点是否正常工作，包括：

1. **健康检查测试** - 验证服务器是否正常运行
2. **认证测试** - 测试登录、登出、获取用户信息
3. **项目测试** - 测试创建项目、获取项目列表
4. **里程碑测试** - 测试创建里程碑
5. **消息测试** - 测试获取未读消息数

测试流程：
- 自动创建测试数据库
- 创建测试用户（管理员和普通用户）
- 依次执行各项测试
- 自动清理测试数据

### 数据库测试 (test_db.py)

测试数据库操作是否正常，包括：

1. **连接测试** - 验证数据库连接
2. **用户操作** - 测试创建用户、密码哈希
3. **项目操作** - 测试创建项目
4. **里程碑操作** - 测试创建里程碑
5. **外键约束** - 测试数据完整性
6. **工具函数** - 测试 UUID 生成等

## 测试数据

### test_data 目录

用于存放测试用文件：

- **sample.xlsx** - 用于测试文件上传功能的示例 Excel 文件
- **sample.pdf** - 用于测试文件上传功能的示例 PDF 文件

如果需要测试文件上传功能，可以在此目录下放置测试文件。

## 清理测试数据

测试过程中会创建临时数据库文件，测试结束后可以手动清理：

```bash
# 删除测试数据库
rm test/test_yourwork.db
rm test/test_db_yourwork.db

# 删除整个测试目录
rm -rf test/
```

## 注意事项

1. 测试数据库独立于生产数据库，不会影响实际数据
2. 测试会在 `test/` 目录下创建临时数据库文件
3. 运行测试前确保已安装所有依赖（`pip install -r requirements.txt`）
4. 部分测试需要服务器正在运行

## 添加新测试

要添加新的测试，请按以下格式：

```python
def test_your_test_name(self):
    """测试描述"""
    # 测试代码
    result = your_function()
    self.assertEqual(result, expected_result)
```

测试方法应以 `test_` 开头，并包含清晰的文档字符串。
