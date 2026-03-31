"""
YourWork - 测试运行器
统一的测试执行入口，支持运行不同类型的测试
"""

import sys
import os
import unittest
import argparse
from datetime import datetime
import json

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.test_base import TestBase, APITestBase, DatabaseTestBase
from test.test_config import TestConfig


class TestRunner:
    """测试运行器"""

    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None

    def run_all_tests(self, verbose=True):
        """运行所有测试"""
        print("=" * 60)
        print("YourWork 测试套件")
        print("=" * 60)
        print()

        self.start_time = datetime.now()

        # 运行单元测试
        print("[1/3] 运行单元测试...")
        unit_result = self.run_unit_tests(verbose)

        # 运行集成测试
        print("\n[2/3] 运行集成测试...")
        integration_result = self.run_integration_tests(verbose)

        # 运行系统测试
        print("\n[3/3] 运行系统测试...")
        system_result = self.run_system_tests(verbose)

        self.end_time = datetime.now()

        # 汇总结果
        self.results = {
            "unit": unit_result,
            "integration": integration_result,
            "system": system_result
        }

        # 打印汇总
        self.print_summary()

        return self.all_passed()

    def run_unit_tests(self, verbose=True):
        """运行单元测试"""
        from test.unit import (
            test_utils,
            test_database,
            test_auth_module
        )

        loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        # 加载单元测试
        suite.addTests(loader.loadTestsFromModule(test_utils))
        suite.addTests(loader.loadTestsFromModule(test_database))
        suite.addTests(loader.loadTestsFromModule(test_auth_module))

        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)

        return {
            "tests_run": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "success": result.wasSuccessful()
        }

    def run_integration_tests(self, verbose=True):
        """运行集成测试"""
        from test.integration import (
            test_auth_flow,
            test_project_flow,
            test_milestone_flow
        )

        loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        # 加载集成测试
        suite.addTests(loader.loadTestsFromModule(test_auth_flow))
        suite.addTests(loader.loadTestsFromModule(test_project_flow))
        suite.addTests(loader.loadTestsFromModule(test_milestone_flow))

        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)

        return {
            "tests_run": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "success": result.wasSuccessful()
        }

    def run_system_tests(self, verbose=True):
        """运行系统测试"""
        from test.system import (
            test_end_to_end,
            test_scenarios
        )

        loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        # 加载系统测试
        suite.addTests(loader.loadTestsFromModule(test_end_to_end))
        suite.addTests(loader.loadTestsFromModule(test_scenarios))

        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        result = runner.run(suite)

        return {
            "tests_run": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "success": result.wasSuccessful()
        }

    def run_specific_test(self, test_path, verbose=True):
        """运行特定测试"""
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromName(test_path)
        runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
        return runner.run(suite)

    def print_summary(self):
        """打印测试汇总"""
        duration = (self.end_time - self.start_time).total_seconds()

        total_tests = sum(r["tests_run"] for r in self.results.values())
        total_failures = sum(r["failures"] for r in self.results.values())
        total_errors = sum(r["errors"] for r in self.results.values())

        print("\n" + "=" * 60)
        print("测试汇总")
        print("=" * 60)

        for test_type, result in self.results.items():
            status = "[OK] 通过" if result["success"] else "[FAIL] 失败"
            print(f"{test_type.upper():12} : {result['tests_run']:3} tests, "
                  f"{result['failures']} failed, {result['errors']} errors | {status}")

        print("-" * 60)
        print(f"{'总计':12} : {total_tests:3} 测试, "
              f"{total_failures} 失败, {total_errors} 错误")

        print(f"\n耗时: {duration:.2f} 秒")
        print("=" * 60)

        if self.all_passed():
            print("[OK] All tests passed!")
        else:
            print("[FAIL] Some tests failed, please check details above")

    def all_passed(self):
        """检查是否所有测试都通过"""
        return all(r["success"] for r in self.results.values())

    def save_report(self, output_path=None):
        """保存测试报告"""
        if output_path is None:
            output_path = os.path.join(
                os.path.dirname(__file__),
                "reports",
                f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        report = {
            "timestamp": datetime.now().isoformat(),
            "duration": (self.end_time - self.start_time).total_seconds(),
            "results": self.results,
            "all_passed": self.all_passed()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n测试报告已保存到: {output_path}")
        return output_path


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="YourWork 测试运行器")
    parser.add_argument("--type", choices=["all", "unit", "integration", "system", "specific"],
                       default="all", help="测试类型")
    parser.add_argument("--test", help="特定测试路径 (当 type=specific 时使用)")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--report", "-r", action="store_true", help="生成测试报告")
    parser.add_argument("--output", "-o", help="报告输出路径")

    args = parser.parse_args()

    runner = TestRunner()
    verbose = args.verbose or True

    if args.type == "all":
        success = runner.run_all_tests(verbose)
    elif args.type == "unit":
        result = runner.run_unit_tests(verbose)
        success = result["success"]
    elif args.type == "integration":
        result = runner.run_integration_tests(verbose)
        success = result["success"]
    elif args.type == "system":
        result = runner.run_system_tests(verbose)
        success = result["success"]
    elif args.type == "specific":
        if not args.test:
            print("错误: 使用 --type=specific 时必须提供 --test 参数")
            sys.exit(1)
        result = runner.run_specific_test(args.test, verbose)
        success = result.wasSuccessful()

    if args.report:
        runner.save_report(args.output)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
