#!/usr/bin/env python3
"""
SSlogs 配置向导
交互式配置生成工具
"""
import os
import sys
import yaml
from pathlib import Path
from typing import Dict, Any


class ConfigWizard:
    """配置向导类"""

    def __init__(self):
        """初始化配置向导"""
        self.config = {}
        self.project_root = Path(__file__).parent.parent

    def print_banner(self):
        """打印欢迎横幅"""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║         SSlogs 配置向导 v3.1                               ║
║    企业级智能安全日志分析平台                              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """
        print(banner)

    def ask_question(self, question: str, default: Any = None,
                     choices: list = None) -> Any:
        """
        提问并获取用户输入

        Args:
            question: 问题文本
            default: 默认值
            choices: 可选值列表

        Returns:
            用户输入的值
        """
        prompt = question

        if choices:
            prompt += f"\n选项: {', '.join(map(str, choices))}"

        if default is not None:
            prompt += f"\n默认值: {default}"

        prompt += "\n请输入: "

        while True:
            user_input = input(prompt).strip()

            # 使用默认值
            if not user_input and default is not None:
                return default

            # 验证选项
            if choices and user_input not in [str(c) for c in choices]:
                print(f"无效输入，请选择: {', '.join(map(str, choices))}")
                continue

            # 类型转换
            if default is not None:
                if isinstance(default, bool):
                    return user_input.lower() in ['true', 'yes', 'y', '1']
                elif isinstance(default, int):
                    try:
                        return int(user_input)
                    except ValueError:
                        print(f"请输入一个整数")
                        continue
                elif isinstance(default, float):
                    try:
                        return float(user_input)
                    except ValueError:
                        print(f"请输入一个数字")
                        continue

            return user_input

    def configure_basic(self) -> Dict[str, Any]:
        """配置基本设置"""
        print("\n" + "="*60)
        print("📋 基本设置")
        print("="*60)

        basic_config = {
            "app_name": "SSlogs",
            "version": "3.1.0",
            "debug": self.ask_question(
                "是否启用调试模式?",
                default=False
            ),
            "timezone": self.ask_question(
                "时区设置",
                default="Asia/Shanghai"
            ),
        }

        return {"basic": basic_config}

    def configure_log_parser(self) -> Dict[str, Any]:
        """配置日志解析器"""
        print("\n" + "="*60)
        print("🔍 日志解析器配置")
        print("="*60)

        parser_config = {
            "timestamp_format": self.ask_question(
                "时间戳格式",
                default="%Y-%m-%d %H:%M:%S"
            ),
            "field_separator": self.ask_question(
                "字段分隔符",
                default=","
            ),
            "encoding": self.ask_question(
                "日志文件编码",
                default="utf-8",
                choices=["utf-8", "gbk", "latin1"]
            ),
            "batch_size": self.ask_question(
                "批处理大小",
                default=100
            ),
        }

        return {"log_parser": parser_config}

    def configure_ai_analyzer(self) -> Dict[str, Any]:
        """配置 AI 分析器"""
        print("\n" + "="*60)
        print("🤖 AI 分析器配置")
        print("="*60)

        print("\n可用的 AI 提供商:")
        print("  1. DeepSeek (云服务)")
        print("  2. Ollama (本地)")
        print("  3. LM Studio (本地)")
        print("  4. 禁用 AI 分析")

        ai_choice = self.ask_question(
            "选择 AI 提供商",
            default="2",
            choices=["1", "2", "3", "4"]
        )

        ai_config = {
            "enabled": ai_choice != "4",
        }

        if ai_choice == "1":
            # DeepSeek 配置
            ai_config.update({
                "provider": "deepseek",
                "api_key": self.ask_question("DeepSeek API 密钥"),
                "api_base": self.ask_question(
                    "API 基础 URL",
                    default="https://api.deepseek.com"
                ),
                "model": self.ask_question(
                    "模型名称",
                    default="deepseek-chat"
                ),
                "timeout": self.ask_question(
                    "请求超时（秒）",
                    default=30
                ),
            })
        elif ai_choice == "2":
            # Ollama 配置
            ai_config.update({
                "provider": "ollama",
                "api_url": self.ask_question(
                    "Ollama API URL",
                    default="http://localhost:11434"
                ),
                "model": self.ask_question(
                    "模型名称",
                    default="llama2"
                ),
                "timeout": self.ask_question(
                    "请求超时（秒）",
                    default=60
                ),
            })
        elif ai_choice == "3":
            # LM Studio 配置
            ai_config.update({
                "provider": "lm_studio",
                "api_url": self.ask_question(
                    "LM Studio API URL",
                    default="http://localhost:1234/v1"
                ),
                "model": self.ask_question(
                    "模型名称",
                    default="local-model"
                ),
                "timeout": self.ask_question(
                    "请求超时（秒）",
                    default=60
                ),
            })
        else:
            # 禁用 AI
            ai_config["enabled"] = False

        # AI 分析参数
        if ai_config["enabled"]:
            ai_config["analysis"] = {
                "enable_threat_detection": self.ask_question(
                    "启用威胁检测?",
                    default=True
                ),
                "enable_behavior_analysis": self.ask_question(
                    "启用行为分析?",
                    default=True
                ),
                "min_confidence": self.ask_question(
                    "最小置信度阈值 (0.0-1.0)",
                    default=0.7
                ),
            }

        return {"ai_analyzer": ai_config}

    def configure_performance(self) -> Dict[str, Any]:
        """配置性能选项"""
        print("\n" + "="*60)
        print("⚡ 性能配置")
        print("="*60)

        perf_config = {
            "max_workers": self.ask_question(
                "最大工作线程数 (0=自动)",
                default=0
            ) or None,
            "batch_size": self.ask_question(
                "批处理大小",
                default=100
            ),
            "memory_limit_mb": self.ask_question(
                "内存限制 (MB, 0=不限制)",
                default=0
            ) or None,
            "enable_caching": self.ask_question(
                "启用缓存?",
                default=True
            ),
            "cache_ttl": self.ask_question(
                "缓存过期时间（秒）",
                default=3600
            ),
        }

        return {"performance": perf_config}

    def configure_output(self) -> Dict[str, Any]:
        """配置输出选项"""
        print("\n" + "="*60)
        print("📊 输出配置")
        print("="*60)

        output_config = {
            "output_dir": self.ask_question(
                "输出目录",
                default="output"
            ),
            "log_dir": self.ask_question(
                "日志目录",
                default="logs"
            ),
            "report_format": self.ask_question(
                "报告格式",
                default="html",
                choices=["html", "json", "csv", "txt"]
            ),
            "include_charts": self.ask_question(
                "包含图表?",
                default=True
            ),
            "save_raw_data": self.ask_question(
                "保存原始数据?",
                default=False
            ),
        }

        return {"output": output_config}

    def run(self) -> Dict[str, Any]:
        """运行配置向导"""
        self.print_banner()

        print("\n欢迎使用 SSlogs 配置向导！")
        print("本向导将帮助您创建配置文件。\n")

        # 逐步配置各个部分
        self.config.update(self.configure_basic())
        self.config.update(self.configure_log_parser())
        self.config.update(self.configure_ai_analyzer())
        self.config.update(self.configure_performance())
        self.config.update(self.configure_output())

        return self.config

    def save_config(self, filename: str = "config.yaml"):
        """
        保存配置到文件

        Args:
            filename: 配置文件名
        """
        config_path = self.project_root / filename

        # 备份现有配置
        if config_path.exists():
            backup_path = config_path.with_suffix('.yaml.bak')
            import shutil
            shutil.copy2(config_path, backup_path)
            print(f"\n✓ 已备份现有配置到: {backup_path}")

        # 保存新配置
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)

        print(f"\n✓ 配置已保存到: {config_path}")
        print("\n配置预览:")
        print("="*60)
        print(yaml.dump(self.config, allow_unicode=True, default_flow_style=False))
        print("="*60)

    def create_env_file(self):
        """创建 .env 文件"""
        env_path = self.project_root / ".env"

        env_vars = []
        if "ai_analyzer" in self.config:
            ai_config = self.config["ai_analyzer"]
            if ai_config.get("enabled"):
                if ai_config.get("provider") == "deepseek":
                    if "api_key" in ai_config:
                        env_vars.append(f'DEEPSEEK_API_KEY={ai_config["api_key"]}')

        if env_vars:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write("# SSlogs 环境变量\n")
                f.write("# 生成时间: " + str(os.popen('date').read().strip()) + "\n\n")
                f.write("\n".join(env_vars))

            print(f"\n✓ 环境变量已保存到: {env_path}")


def main():
    """主函数"""
    wizard = ConfigWizard()

    try:
        # 运行向导
        config = wizard.run()

        # 保存配置
        save = input("\n是否保存配置? (Y/n): ").strip().lower()
        if save in ['', 'y', 'yes']:
            wizard.save_config()
            wizard.create_env_file()

            print("\n✅ 配置完成！")
            print("\n下一步:")
            print("  1. 检查配置文件: config.yaml")
            print("  2. 如有需要，编辑 .env 文件添加敏感信息")
            print("  3. 运行: python start_optimized_gui.py")
        else:
            print("\n配置未保存。")

    except KeyboardInterrupt:
        print("\n\n❌ 配置已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
