import sys
import os

# 添加项目根目录到Python路径，以便导入模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox,
                             QProgressBar, QTextEdit, QFileDialog, QMessageBox, QGroupBox,
                             QTabWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

# 导入主程序模块
from main import LogHunter
from core.ai_analyzer import AIAnalyzer

class AnalysisWorker(QThread):
    """分析工作线程"""
    # 信号定义
    progress_updated = pyqtSignal(int, str)
    log_output = pyqtSignal(str)
    analysis_finished = pyqtSignal(bool, str)
    
    def __init__(self, log_path, server_ip, output_dir, report_format, ai_enabled,
                 model_type=None, model_name=None, api_key=None):
        super().__init__()
        self.log_path = log_path
        self.server_ip = server_ip
        self.output_dir = output_dir
        self.report_format = report_format
        self.ai_enabled = ai_enabled
        self.model_type = model_type
        self.model_name = model_name
        self.api_key = api_key
        self.is_interrupted = False
    
    def run(self):
        """在后台线程中执行分析"""
        try:
            # 初始化LogHunter
            self.log_output.emit("初始化分析器...")
            
            log_hunter = LogHunter('config.yaml', ai_enabled=self.ai_enabled, 
                                 server_ip=self.server_ip, disable_signal_handlers=True)
            
            # 更新配置
            log_hunter.config['output_dir'] = self.output_dir
            log_hunter.config['report_type'] = self.report_format
            log_hunter.config['log_path'] = self.log_path
            
            # 重定向日志输出
            import logging
            handler = logging.StreamHandler(self)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            
            # 为LogHunter的logger添加handler
            log_hunter.logger.addHandler(handler)
            log_hunter.logger.setLevel(logging.INFO)
            
            # 更新进度
            self.progress_updated.emit(10, "开始分析...")
            
            # 运行分析
            log_hunter.run()
            
            # 更新进度和状态
            self.progress_updated.emit(100, "分析完成")
            self.analysis_finished.emit(True, "分析成功完成")
            
        except Exception as e:
            error_msg = f"分析过程中发生错误: {str(e)}"
            self.progress_updated.emit(0, error_msg)
            self.analysis_finished.emit(False, error_msg)

class LogAnalyzerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("应急分析溯源日志工具 - PyQt6版")
        self.setGeometry(100, 100, 900, 700)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        
        # 创建输入区域
        self.create_input_area(main_layout)
        
        # 创建进度和日志区域
        self.create_progress_and_log_area(main_layout)
        
        # 创建分析按钮
        self.create_analysis_button(main_layout)
        
        # 初始化变量
        self.worker = None
        
        # 连接模型类型切换信号
        self.model_type_combo.currentTextChanged.connect(self.on_model_type_changed)
        
        # 初始化模型类型
        self.on_model_type_changed()
    
    def create_input_area(self, parent_layout):
        """创建输入区域"""
        # 创建选项卡控件
        tab_widget = QTabWidget()
        
        # 创建主设置选项卡
        main_tab = QWidget()
        main_layout = QVBoxLayout(main_tab)
        
        # 日志目录选择
        log_layout = QHBoxLayout()
        log_label = QLabel("日志目录:")
        self.log_path_input = QLineEdit("logs/*.log")
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_log_path)
        
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_path_input)
        log_layout.addWidget(browse_btn)
        
        # AI分析复选框
        self.ai_checkbox = QCheckBox("启用AI分析")
        
        # 主机IP地址输入
        ip_layout = QHBoxLayout()
        ip_label = QLabel("主机IP地址:")
        self.ip_input = QLineEdit()
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_input)
        
        # 输出目录选择
        output_layout = QHBoxLayout()
        output_label = QLabel("输出报告目录:")
        self.output_dir_input = QLineEdit("output")
        output_browse_btn = QPushButton("浏览...")
        output_browse_btn.clicked.connect(self.browse_output_dir)
        
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_dir_input)
        output_layout.addWidget(output_browse_btn)
        
        # 报告格式选择
        format_layout = QHBoxLayout()
        format_label = QLabel("报告格式:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["html", "json", "txt"])
        self.format_combo.setCurrentText("html")
        
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        
        # 添加到主选项卡布局
        main_layout.addLayout(log_layout)
        main_layout.addWidget(self.ai_checkbox)
        main_layout.addLayout(ip_layout)
        main_layout.addLayout(output_layout)
        main_layout.addLayout(format_layout)
        
        # 创建AI配置选项卡
        ai_tab = QWidget()
        ai_layout = QVBoxLayout(ai_tab)
        
        # AI模型类型选择
        model_type_layout = QHBoxLayout()
        model_type_label = QLabel("AI模型类型:")
        self.model_type_combo = QComboBox()
        self.model_type_combo.addItems(["云端 (SiliconFlow)", "本地 (Ollama)"])
        self.model_type_combo.setCurrentText("云端 (SiliconFlow)")
        
        model_type_layout.addWidget(model_type_label)
        model_type_layout.addWidget(self.model_type_combo)
        
        # 模型选择
        model_layout = QHBoxLayout()
        model_label = QLabel("模型名称:")
        self.model_name_input = QLineEdit()
        self.model_name_input.setPlaceholderText("例如: deepseek-ai/DeepSeek-V3 或 deepseek-r1:14b")
        
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_name_input)
        
        # API密钥输入（仅在云端模式下显示）
        self.api_key_layout = QHBoxLayout()
        api_key_label = QLabel("API密钥:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("输入API密钥")
        
        self.api_key_layout.addWidget(api_key_label)
        self.api_key_layout.addWidget(self.api_key_input)
        
        # 添加到AI选项卡布局
        ai_layout.addLayout(model_type_layout)
        ai_layout.addLayout(model_layout)
        ai_layout.addLayout(self.api_key_layout)
        
        # 添加测试按钮
        self.test_ai_button = QPushButton("测试AI连接")
        self.test_ai_button.clicked.connect(self.test_ai_connection)
        
        ai_layout.addWidget(self.test_ai_button)
        
        # 添加选项卡
        tab_widget.addTab(main_tab, "基本设置")
        tab_widget.addTab(ai_tab, "AI配置")
        
        parent_layout.addWidget(tab_widget)
    
    def on_model_type_changed(self):
        """当模型类型改变时更新界面"""
        model_type = self.model_type_combo.currentText()
        
        # 根据模型类型显示/隐藏API密钥输入框
        if model_type == "云端 (SiliconFlow)":
            self.api_key_input.setVisible(True)
            self.model_name_input.setPlaceholderText("例如: deepseek-ai/DeepSeek-V3")
        else:  # 本地 (Ollama)
            self.api_key_input.setVisible(False)
            self.model_name_input.setPlaceholderText("例如: deepseek-r1:14b")
    
    def browse_log_path(self):
        """选择日志目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择日志目录")
        if directory:
            self.log_path_input.setText(directory)
    
    def browse_output_dir(self):
        """选择输出目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            self.output_dir_input.setText(directory)
    
    def test_ai_connection(self):
        """测试AI连接"""
        try:
            # 获取配置信息
            model_type = self.model_type_combo.currentText()
            
            if model_type == "云端 (SiliconFlow)":
                # 检查API密钥
                api_key = self.api_key_input.text().strip()
                if not api_key:
                    QMessageBox.warning(self, "警告", "请先输入API密钥")
                    return
                    
                # 创建AI分析器测试连接
                ai_analyzer = AIAnalyzer(config_path='config.yaml')
                
                # 测试简单的AI分析
                test_context = "测试连接"
                result = ai_analyzer.analyze_log(test_context)
                
                if "失败" in result:
                    QMessageBox.warning(self, "连接测试", f"AI连接测试失败:\n{result}")
                else:
                    QMessageBox.information(self, "连接测试", "AI连接成功！")
                    
            else:  # 本地 (Ollama)
                # 检查Ollama是否运行
                ai_analyzer = AIAnalyzer(config_path='config.yaml')
                
                # 测试简单的AI分析
                test_context = "测试连接"
                result = ai_analyzer.analyze_log(test_context)
                
                if "失败" in result:
                    QMessageBox.warning(self, "连接测试", f"本地AI连接测试失败:\n{result}")
                else:
                    QMessageBox.information(self, "连接测试", "本地AI连接成功！")
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"测试AI连接时发生错误:\n{str(e)}")
    
    def start_analysis(self):
        """开始分析"""
        # 获取用户输入
        log_path = self.log_path_input.text().strip()
        server_ip = self.ip_input.text().strip()
        output_dir = self.output_dir_input.text().strip()
        report_format = self.format_combo.currentText()
        ai_enabled = self.ai_checkbox.isChecked()
        
        # 获取AI配置
        model_type = self.model_type_combo.currentText()
        model_name = self.model_name_input.text().strip()
        api_key = self.api_key_input.text().strip()
        
        # 验证输入
        if not log_path:
            QMessageBox.critical(self, "错误", "请指定日志目录")
            return
            
        if not server_ip:
            QMessageBox.critical(self, "错误", "请输入主机IP地址")
            return
            
        # 如果启用了AI分析，需要验证配置
        if ai_enabled:
            if model_type == "云端 (SiliconFlow)":
                if not api_key:
                    QMessageBox.critical(self, "错误", "请提供API密钥")
                    return
                if not model_name:
                    QMessageBox.critical(self, "错误", "请指定云端模型名称")
                    return
            else:  # 本地 (Ollama)
                if not model_name:
                    QMessageBox.critical(self, "错误", "请指定本地模型名称")
                    return
        
        # 禁用分析按钮，显示正在处理
        self.analyze_button.setEnabled(False)
        self.progress_label.setText("开始分析...")
        
        # 创建并启动工作线程
        self.worker = AnalysisWorker(log_path, server_ip, output_dir, report_format, ai_enabled,
                                   model_type, model_name, api_key)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.log_output.connect(self.append_log)
        self.worker.analysis_finished.connect(self.analysis_completed)
        
        # 启动线程
        self.worker.start()
    
    def create_progress_and_log_area(self, parent_layout):
        """创建进度和日志区域"""
        # 进度条区域
        progress_group = QGroupBox("分析进度")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("准备就绪")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        
        progress_group.setLayout(progress_layout)
        parent_layout.addWidget(progress_group)
        
        # 日志输出区域
        log_group = QGroupBox("分析日志")
        log_layout = QVBoxLayout()
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        font = QFont("Monospace")
        font.setPointSize(9)
        self.log_output.setFont(font)
        
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)
        parent_layout.addWidget(log_group)
    
    def create_analysis_button(self, parent_layout):
        """创建分析按钮"""
        button_layout = QHBoxLayout()
        
        self.analyze_button = QPushButton("开始分析")
        self.analyze_button.clicked.connect(self.start_analysis)
        
        # 添加一些间距
        button_layout.addStretch()
        button_layout.addWidget(self.analyze_button)
        button_layout.addStretch()
        
        parent_layout.addLayout(button_layout)
    
    def update_progress(self, value, message):
        """更新进度条"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
    
    def append_log(self, message):
        """添加日志输出"""
        self.log_output.append(message)
        # 自动滚动到底部
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def analysis_completed(self, success, message):
        """分析完成"""
        self.analyze_button.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "完成", message)
        else:
            QMessageBox.critical(self, "错误", message)

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("应急分析溯源日志工具")
    app.setApplicationVersion("1.0")
    
    # 创建并显示主窗口
    window = LogAnalyzerGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()