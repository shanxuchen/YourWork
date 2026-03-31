"""
YourWork - 数据库测试（兼容版本）
使用新测试框架的数据库测试入口
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.test_runner import TestRunner


def main():
    """运行数据库测试"""
    print("=" * 60)
    print("YourWork 数据库测试")
    print("=" * 60)
    print()

    runner = TestRunner()
    success = runner.run_unit_tests(verbose=True)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
