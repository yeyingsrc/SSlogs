import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径，以便导入模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import LogHunter

class LogAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("应急分析溯源日志工具")
        self.root.geometry("800x700")
        
        # 创建主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 日志目录选择
        ttk.Label(main_frame, text="日志目录:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.log_path_var = tk.StringVar()
        log_entry = ttk.Entry(main_frame, textvariable=self.log_path_var, width=50)
        log_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        browse_btn = ttk.Button(main_frame, text="浏览", command=self.browse_log_path)
        browse_btn.grid(row=0, column=2, sticky=tk.W, pady=5, padx=(5, 0))
        
        # AI分析复选框
        self.ai_enabled_var = tk.BooleanVar()
        ai_check = ttk.Checkbutton(main_frame, text="启用AI分析", variable=self.ai_enabled_var)
        ai_check.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # 主机IP地址输入
        ttk.Label(main_frame, text="主机IP地址:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.server_ip_var = tk.StringVar()
        ip_entry = ttk.Entry(main_frame, textvariable=self.server_ip_var, width=50)
        ip_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        
        # 输出目录选择
        ttk.Label(main_frame, text="输出报告目录:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.output_dir_var = tk.StringVar()
        output_entry = ttk.Entry(main_frame, textvariable=self.output_dir_var, width=50)
        output_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        output_browse_btn = ttk.Button(main_frame, text="浏览", command=self.browse_output_dir)
        output_browse_btn.grid(row=3, column=2, sticky=tk.W, pady=5, padx=(5, 0))
        
        # 报告格式选择
        ttk.Label(main_frame, text="报告格式:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.report_format_var = tk.StringVar(value="html")
        format_combo = ttk.Combobox(main_frame, textvariable=self.report_format_var, 
                                   values=["html", "json", "txt"], state="readonly", width=47)
        format_combo.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        
        # 进度条
        ttk.Label(main_frame, text="分析进度:").grid(row=5, column=0, sticky=tk.W, pady=10)
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=10, padx=(5, 0))
        self.progress_label = ttk.Label(main_frame, text="准备就绪")
        self.progress_label.grid(row=6, column=1, sticky=tk.W, pady=(0, 10), padx=(5, 0))
        
        # 分析按钮
        self.analyze_btn = ttk.Button(main_frame, text="开始分析", command=self.start_analysis)
        self.analyze_btn.grid(row=7, column=0, columnspan=3, pady=20)
        
        # 日志显示区域
        ttk.Label(main_frame, text="分析日志:").grid(row=8, column=0, sticky=tk.W, pady=(10, 5))
        self.log_text = tk.Text(main_frame, height=10, width=80)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=9, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        scrollbar.grid(row=9, column=3, sticky=(tk.N, tk.S), pady=(0, 10))
        
        # 配置网格权重
        main_frame.rowconfigure(9, weight=1)
        
        # 初始化默认值
        self.log_path_var.set("logs/*.log")
        self.output_dir_var.set("output")
        
    def _update_progress(self, value):
        """更新进度条值"""
        self.progress['value'] = value
        
    def browse_log_path(self):
        """选择日志目录"""
        directory = filedialog.askdirectory()
        if directory:
            self.log_path_var.set(directory)
    
    def browse_output_dir(self):
        """选择输出目录"""
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_var.set(directory)
    
    def start_analysis(self):
        """开始分析"""
        # 获取用户输入
        log_path = self.log_path_var.get().strip()
        server_ip = self.server_ip_var.get().strip()
        output_dir = self.output_dir_var.get().strip()
        report_format = self.report_format_var.get()
        
        # 验证输入
        if not log_path:
            messagebox.showerror("错误", "请指定日志目录")
            return
            
        if not server_ip:
            messagebox.showerror("错误", "请输入主机IP地址")
            return
            
        # 禁用分析按钮，显示正在处理
        self.analyze_btn.config(state="disabled")
        self.progress_label.config(text="开始分析...")
        
        # 在新线程中运行分析，避免界面冻结
        thread = threading.Thread(target=self.run_analysis, 
                                args=(log_path, server_ip, output_dir, report_format))
        thread.daemon = True
        thread.start()
    
    def run_analysis(self, log_path, server_ip, output_dir, report_format):
        """在后台线程中运行分析"""
        try:
            # 更新UI
            self.root.after(0, lambda: self.progress_label.config(text="初始化分析器..."))
            
            # 创建LogHunter实例
            log_hunter = LogHunter('config.yaml', ai_enabled=self.ai_enabled_var.get(), 
                                 server_ip=server_ip)
            
            # 更新配置中的输出目录
            log_hunter.config['output_dir'] = output_dir
            log_hunter.config['report_type'] = report_format
            
            # 更新日志路径
            log_hunter.config['log_path'] = log_path
            
            # 重定向日志输出到GUI
            import logging
            handler = logging.StreamHandler(self)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            
            # 为LogHunter的logger添加handler
            log_hunter.logger.addHandler(handler)
            log_hunter.logger.setLevel(logging.INFO)
            
            # 更新进度条
            self.root.after(0, self._update_progress, 10)
            
            # 运行分析
            log_hunter.run()
            
            # 更新进度条和状态
            self.root.after(0, self._update_progress, 100)
            self.root.after(0, lambda: self.progress_label.config(text="分析完成"))
            
        except Exception as e:
            error_msg = f"分析过程中发生错误: {str(e)}"
            self.root.after(0, lambda: self.progress_label.config(text=error_msg))
            messagebox.showerror("错误", error_msg)
        finally:
            # 恢复分析按钮
            self.root.after(0, lambda: self.analyze_btn.config(state="normal"))
    
    def write(self, message):
        """重写write方法，将日志输出到GUI文本框"""
        self.root.after(0, lambda: self.log_text.insert(tk.END, message + '\n'))
        self.root.after(0, lambda: self.log_text.see(tk.END))
    
    def flush(self):
        """重写flush方法"""
        pass

def main():
    root = tk.Tk()
    app = LogAnalyzerGUI(root)
    
    # 设置窗口关闭事件
    def on_closing():
        if messagebox.askokcancel("退出", "确定要退出应急分析溯源日志工具吗？"):
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()