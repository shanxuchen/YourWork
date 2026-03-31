"""
WebSocket 测试运行器
统一运行所有 WebSocket 测试
"""

import os
import sys
import unittest
import time
from io import StringIO

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class WebSocketTestRunner:
    """WebSocket 测试运行器"""

    def __init__(self):
        self.test_results = {
            "unit": {"passed": 0, "failed": 0, "errors": [], "duration": 0},
            "integration": {"passed": 0, "failed": 0, "errors": [], "duration": 0},
            "system": {"passed": 0, "failed": 0, "errors": [], "duration": 0}
        }

    def run_all_tests(self, verbosity=2):
        """运行所有测试"""
        print("=" * 70)
        print("WebSocket 测试套件")
        print("=" * 70)
        print()

        # 运行单元测试
        print("[1/3] 运行单元测试...")
        print("-" * 70)
        self._run_test_suite("unit", "test.websocket.unit", verbosity)

        # 运行集成测试
        print()
        print("[2/3] 运行集成测试...")
        print("-" * 70)
        self._run_test_suite("integration", "test.websocket.integration", verbosity)

        # 运行系统测试
        print()
        print("[3/3] 运行系统/流程测试...")
        print("-" * 70)
        self._run_test_suite("system", "test.websocket.system", verbosity)

        # 输出测试报告
        self._print_summary()

        return self._is_all_passed()

    def run_unit_tests(self, verbosity=2):
        """仅运行单元测试"""
        print("=" * 70)
        print("WebSocket 单元测试")
        print("=" * 70)
        self._run_test_suite("unit", "test.websocket.unit", verbosity)
        self._print_summary("unit")
        return self.test_results["unit"]["failed"] == 0

    def run_integration_tests(self, verbosity=2):
        """仅运行集成测试"""
        print("=" * 70)
        print("WebSocket 集成测试")
        print("=" * 70)
        self._run_test_suite("integration", "test.websocket.integration", verbosity)
        self._print_summary("integration")
        return self.test_results["integration"]["failed"] == 0

    def run_system_tests(self, verbosity=2):
        """仅运行系统测试"""
        print("=" * 70)
        print("WebSocket 系统/流程测试")
        print("=" * 70)
        self._run_test_suite("system", "test.websocket.system", verbosity)
        self._print_summary("system")
        return self.test_results["system"]["failed"] == 0

    def _run_test_suite(self, suite_type, module_path, verbosity):
        """运行测试套件"""
        start_time = time.time()

        # 创建测试套件
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromName(module_path)

        # 创建测试运行器
        stream = StringIO()
        runner = unittest.TextTestRunner(stream=stream, verbosity=verbosity)

        # 运行测试
        result = runner.run(suite)

        # 记录结果
        duration = time.time() - start_time
        self.test_results[suite_type] = {
            "passed": result.testsRun - len(result.failures) - len(result.errors),
            "failed": len(result.failures),
            "errors": len(result.errors),
            "duration": duration,
            "total": result.testsRun
        }

        # 输出结果
        if suite_type == "unit":
            print(f"[OK] 单元测试完成: {self.test_results[suite_type]['passed']}/{result.testsRun} 通过")
        elif suite_type == "integration":
            print(f"[OK] 集成测试完成: {self.test_results[suite_type]['passed']}/{result.testsRun} 通过")
        else:
            print(f"[OK] 系统测试完成: {self.test_results[suite_type]['passed']}/{result.testsRun} 通过")

    def _print_summary(self, suite_type=None):
        """打印测试摘要"""
        if suite_type:
            self._print_suite_summary(suite_type)
        else:
            self._print_overall_summary()

    def _print_suite_summary(self, suite_type):
        """打印单个套件摘要"""
        results = self.test_results[suite_type]
        print(f"""
  ├─ 通过: {results['passed']}
  ├─ 失败: {results['failed']}
  ├─ 错误: {results['errors']}
  └─ 耗时: {results['duration']:.2f}秒
""")

    def _print_overall_summary(self):
        """打印整体摘要"""
        print()
        print("=" * 70)
        print("测试摘要")
        print("=" * 70)

        total_passed = sum(r["passed"] for r in self.test_results.values())
        total_failed = sum(r["failed"] for r in self.test_results.values())
        total_errors = sum(r["errors"] for r in self.test_results.values())
        total_tests = total_passed + total_failed + total_errors
        total_duration = sum(r["duration"] for r in self.test_results.values())

        print(f"总测试数: {total_tests}")
        print(f"通过: {total_passed}")
        print(f"失败: {total_failed}")
        print(f"错误: {total_errors}")
        print(f"总耗时: {total_duration:.2f}秒")
        print()

        # 详细分类
        for suite_type, results in self.test_results.items():
            if results.get("total"):
                status = "[OK]" if results["failed"] == 0 else "[FAIL]"
                print(f"{status} {suite_type.upper():12} {results['passed']}/{results['total']} 通过")

        print()
        print("=" * 70)

        if total_failed == 0 and total_errors == 0:
            print("[OK] 所有测试通过!")
            return True
        else:
            print("[FAIL] 存在失败的测试")
            return False

    def _is_all_passed(self):
        """检查是否所有测试通过"""
        for results in self.test_results.values():
            if results.get("failed", 0) > 0 or results.get("errors", 0) > 0:
                return False
        return True

    def save_report(self, filename="test/websocket_test_report.txt"):
        """保存测试报告到文件"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, "w", encoding="utf-8") as f:
            f.write("WebSocket 测试报告\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # 写入各套件结果
            for suite_type, results in self.test_results.items():
                if results.get("total"):
                    f.write(f"{suite_type.upper()} 测试\n")
                    f.write("-" * 70 + "\n")
                    f.write(f"通过: {results['passed']}\n")
                    f.write(f"失败: {results['failed']}\n")
                    f.write(f"错误: {results['errors']}\n")
                    f.write(f"总计: {results['total']}\n")
                    f.write(f"耗时: {results['duration']:.2f}秒\n")
                    f.write("\n")

        print(f"测试报告已保存到: {filename}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="WebSocket 测试运行器")
    parser.add_argument("--type", choices=["all", "unit", "integration", "system"],
                       default="all", help="测试类型")
    parser.add_argument("-v", "--verbosity", type=int, default=2,
                       help="输出详细程度 (0-2)")
    parser.add_argument("--report", action="store_true",
                       help="生成测试报告文件")

    args = parser.parse_args()

    runner = WebSocketTestRunner()

    if args.type == "unit":
        success = runner.run_unit_tests(args.verbosity)
    elif args.type == "integration":
        success = runner.run_integration_tests(args.verbosity)
    elif args.type == "system":
        success = runner.run_system_tests(args.verbosity)
    else:
        success = runner.run_all_tests(args.verbosity)

    if args.report:
        runner.save_report()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
