#!/usr/bin/env python3
"""
测试运行脚本
"""
import sys
import subprocess
import os


def run_tests():
    """运行所有测试"""
    print("🧪 开始运行GridBNB交易机器人测试套件...")
    print("=" * 60)
    
    # 确保在项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    try:
        # 运行pytest
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            'tests/unit/',
            '-v',           # 详细输出
            '--tb=short',   # 简短的错误回溯
            '--color=yes',  # 彩色输出
            '--durations=10'  # 显示最慢的10个测试
        ], capture_output=False, text=True)
        
        if result.returncode == 0:
            print("\n✅ 所有测试通过！")
            print("🎉 代码质量检查完成，可以安全部署。")
        else:
            print("\n❌ 部分测试失败！")
            print("🔧 请检查失败的测试并修复相关问题。")
            
        return result.returncode
        
    except FileNotFoundError:
        print("❌ 错误：未找到pytest。请先安装测试依赖：")
        print("pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"❌ 运行测试时发生错误: {e}")
        return 1


def run_specific_test(test_file):
    """运行特定的测试文件"""
    print(f"🧪 运行测试文件: {test_file}")
    print("=" * 60)
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            f'tests/{test_file}', 
            '-v',
            '--tb=short',
            '--color=yes'
        ], capture_output=False, text=True)
        
        return result.returncode
        
    except Exception as e:
        print(f"❌ 运行测试时发生错误: {e}")
        return 1


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # 运行特定测试
        test_file = sys.argv[1]
        if not test_file.startswith('test_'):
            test_file = f'test_{test_file}'
        if not test_file.endswith('.py'):
            test_file = f'{test_file}.py'
        
        exit_code = run_specific_test(test_file)
    else:
        # 运行所有测试
        exit_code = run_tests()
    
    sys.exit(exit_code)
