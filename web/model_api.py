#!/usr/bin/env python3
"""
模型管理Web API
提供LM Studio模型管理的HTTP接口
"""

import json
import logging
import asyncio
import time
import requests
from typing import Dict, List, Any, Optional
from pathlib import Path

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

from core.model_manager import get_model_manager, ModelInfo, ServerStatus, reset_model_manager
from core.ai_config_manager import get_ai_config_manager
from core.lm_studio_connector import get_lm_studio_connector

# 创建Flask应用
app = Flask(__name__)
# CORS限制：仅允许本地访问，生产环境应配置实际域名
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局变量
model_manager = get_model_manager()
config_manager = get_ai_config_manager()

# HTML模板
MODEL_MANAGEMENT_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SSlogs - AI模型管理</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
        }

        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }

        .main-content {
            padding: 30px;
        }

        .status-card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
            border-left: 4px solid #4f46e5;
        }

        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .status-item {
            text-align: center;
            padding: 15px;
            background: #f8fafc;
            border-radius: 8px;
        }

        .status-item .value {
            font-size: 1.8rem;
            font-weight: bold;
            color: #4f46e5;
            margin-bottom: 5px;
        }

        .status-item .label {
            color: #64748b;
            font-size: 0.9rem;
        }

        .status-connected {
            border-left-color: #10b981;
        }

        .status-disconnected {
            border-left-color: #ef4444;
        }

        .actions-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            flex-wrap: wrap;
            gap: 15px;
        }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 500;
        }

        .btn-primary {
            background: #4f46e5;
            color: white;
        }

        .btn-primary:hover {
            background: #4338ca;
            transform: translateY(-2px);
        }

        .btn-secondary {
            background: #6b7280;
            color: white;
        }

        .btn-secondary:hover {
            background: #4b5563;
        }

        .btn-success {
            background: #10b981;
            color: white;
        }

        .btn-success:hover {
            background: #059669;
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .models-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .model-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
            border: 2px solid transparent;
            transition: all 0.3s ease;
            position: relative;
        }

        .model-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
        }

        .model-card.selected {
            border-color: #4f46e5;
            background: linear-gradient(to right, rgba(79, 70, 229, 0.05), rgba(79, 70, 229, 0.02));
        }

        .model-card.recommended {
            border-color: #10b981;
        }

        .model-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }

        .model-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 5px;
            word-break: break-word;
        }

        .model-id {
            font-size: 0.85rem;
            color: #6b7280;
            font-family: monospace;
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 4px;
        }

        .model-badges {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }

        .badge {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
        }

        .badge-recommended {
            background: #dcfce7;
            color: #16a34a;
        }

        .badge-current {
            background: #dbeafe;
            color: #2563eb;
        }

        .badge-parameters {
            background: #fef3c7;
            color: #d97706;
        }

        .badge-quantization {
            background: #e0e7ff;
            color: #4f46e5;
        }

        .model-description {
            color: #4b5563;
            font-size: 0.9rem;
            line-height: 1.5;
            margin-bottom: 15px;
        }

        .model-actions {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .btn-small {
            padding: 6px 12px;
            font-size: 0.85rem;
        }

        .compatibility-score {
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 0.85rem;
            color: #6b7280;
        }

        .score-bar {
            width: 50px;
            height: 6px;
            background: #e5e7eb;
            border-radius: 3px;
            overflow: hidden;
        }

        .score-fill {
            height: 100%;
            background: linear-gradient(to right, #ef4444, #eab308, #10b981);
            transition: width 0.3s ease;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #6b7280;
        }

        .spinner {
            border: 3px solid #e5e7eb;
            border-top: 3px solid #4f46e5;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .error-message {
            background: #fef2f2;
            border: 1px solid #fecaca;
            color: #dc2626;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .success-message {
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            color: #16a34a;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
        }

        .modal-content {
            background: white;
            margin: 10% auto;
            padding: 30px;
            border-radius: 12px;
            width: 90%;
            max-width: 600px;
            position: relative;
        }

        .modal-close {
            position: absolute;
            right: 20px;
            top: 20px;
            font-size: 28px;
            cursor: pointer;
            color: #6b7280;
        }

        .modal-close:hover {
            color: #1f2937;
        }

        .test-result {
            background: #f8fafc;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
        }

        .test-response {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 15px;
            margin-top: 10px;
            font-family: monospace;
            white-space: pre-wrap;
            max-height: 300px;
            overflow-y: auto;
        }

        @media (max-width: 768px) {
            .container {
                margin: 10px;
                border-radius: 10px;
            }

            .header {
                padding: 20px;
            }

            .header h1 {
                font-size: 2rem;
            }

            .main-content {
                padding: 20px;
            }

            .models-grid {
                grid-template-columns: 1fr;
            }

            .actions-bar {
                flex-direction: column;
                align-items: stretch;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 SSlogs AI模型管理</h1>
            <p>管理LM Studio本地模型，配置AI安全分析功能</p>
        </div>

        <div class="main-content">
            <!-- 服务器状态 -->
            <div id="status-card" class="status-card">
                <h3>🔗 LM Studio服务器状态</h3>
                <div id="status-content">
                    <div class="loading">
                        <div class="spinner"></div>
                        <p>正在检查服务器状态...</p>
                    </div>
                </div>
            </div>

            <!-- 操作栏 -->
            <div class="actions-bar">
                <div>
                    <button onclick="refreshModels()" class="btn btn-primary">
                        🔄 刷新模型列表
                    </button>
                    <button onclick="getRecommendations()" class="btn btn-secondary">
                        ⭐ 获取推荐
                    </button>
                    <button onclick="openConfigModal()" class="btn btn-secondary">
                        ⚙️ 配置
                    </button>
                    <button onclick="openAPITestModal()" class="btn btn-secondary">
                        🧪 API测试
                    </button>
                </div>
                <div>
                    <select id="useCase" class="btn btn-secondary" style="padding: 10px;">
                        <option value="general">通用用途</option>
                        <option value="security_analysis">安全分析</option>
                        <option value="speed">速度优先</option>
                    </select>
                </div>
            </div>

            <!-- 消息显示区 -->
            <div id="message-area"></div>

            <!-- 模型列表 -->
            <div id="models-container">
                <div class="loading">
                    <div class="spinner"></div>
                    <p>正在加载模型列表...</p>
                </div>
            </div>
        </div>
    </div>

    <!-- 模型测试对话框 -->
    <div id="testModal" class="modal">
        <div class="modal-content">
            <span class="modal-close" onclick="closeTestModal()">&times;</span>
            <h3>🧪 测试模型</h3>
            <p>模型: <strong id="testModelName"></strong></p>

            <div style="margin: 20px 0;">
                <label for="testPrompt" style="display: block; margin-bottom: 5px;">测试提示词:</label>
                <textarea id="testPrompt" style="width: 100%; height: 80px; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px;">你好，请简单介绍一下自己。</textarea>
            </div>

            <button onclick="testModel()" class="btn btn-primary">开始测试</button>

            <div id="testResult" class="test-result" style="display: none;">
                <h4>测试结果:</h4>
                <div id="testResponse"></div>
            </div>
        </div>
    </div>

    <!-- 配置对话框 -->
    <div id="configModal" class="modal">
        <div class="modal-content" style="max-width: 800px;">
            <span class="modal-close" onclick="closeConfigModal()">&times;</span>
            <h3>⚙️ AI配置管理</h3>

            <div style="margin: 20px 0;">
                <h4>LM Studio API配置</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                    <div>
                        <label for="apiBaseUrl" style="display: block; margin-bottom: 5px;">API基础URL:</label>
                        <input type="text" id="apiBaseUrl" style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;" value="http://127.0.0.1:1234/v1">
                    </div>
                    <div>
                        <label for="apiKey" style="display: block; margin-bottom: 5px;">API密钥 (可选):</label>
                        <input type="text" id="apiKey" style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;" placeholder="通常为空">
                    </div>
                </div>
            </div>

            <div style="margin: 20px 0;">
                <h4>模型配置</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                    <div>
                        <label for="preferredModel" style="display: block; margin-bottom: 5px;">首选模型:</label>
                        <input type="text" id="preferredModel" style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;" placeholder="留空自动选择">
                    </div>
                    <div>
                        <label for="maxTokens" style="display: block; margin-bottom: 5px;">最大令牌数:</label>
                        <input type="number" id="maxTokens" style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;" value="2048">
                    </div>
                    <div>
                        <label for="temperature" style="display: block; margin-bottom: 5px;">温度:</label>
                        <input type="number" id="temperature" step="0.1" min="0" max="2" style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;" value="0.7">
                    </div>
                    <div>
                        <label for="topP" style="display: block; margin-bottom: 5px;">Top-P:</label>
                        <input type="number" id="topP" step="0.1" min="0" max="1" style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;" value="0.9">
                    </div>
                </div>
            </div>

            <div style="margin: 20px 0;">
                <h4>模型名称映射</h4>
                <p style="color: #6b7280; font-size: 0.9rem; margin-bottom: 10px;">将实际模型ID映射为自定义名称</p>
                <div id="modelMappings" style="max-height: 200px; overflow-y: auto; border: 1px solid #d1d5db; border-radius: 4px; padding: 10px;">
                    <div style="color: #6b7280; text-align: center;">暂无映射</div>
                </div>
                <div style="margin-top: 10px; display: flex; gap: 10px;">
                    <input type="text" id="newMappingId" placeholder="实际模型ID" style="flex: 1; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;">
                    <input type="text" id="newMappingName" placeholder="显示名称" style="flex: 1; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;">
                    <button onclick="addModelMapping()" class="btn btn-primary btn-small">添加</button>
                </div>
            </div>

            <div style="margin-top: 20px; text-align: right;">
                <button onclick="saveConfig()" class="btn btn-primary">保存配置</button>
                <button onclick="closeConfigModal()" class="btn btn-secondary">取消</button>
            </div>

            <div id="configResult" class="test-result" style="display: none; margin-top: 20px;">
                <div id="configResponse"></div>
            </div>
        </div>
    </div>

    <!-- API测试对话框 -->
    <div id="apiTestModal" class="modal">
        <div class="modal-content" style="max-width: 700px;">
            <span class="modal-close" onclick="closeAPITestModal()">&times;</span>
            <h3>🧪 OpenAI兼容API测试</h3>

            <div style="margin: 20px 0;">
                <h4>API配置</h4>
                <div style="display: grid; grid-template-columns: 1fr; gap: 15px; margin-bottom: 20px;">
                    <div>
                        <label for="testApiUrl" style="display: block; margin-bottom: 5px;">API地址:</label>
                        <input type="text" id="testApiUrl" style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;" value="http://localhost:1234/v1/chat/completions">
                    </div>
                    <div>
                        <label for="testApiKey" style="display: block; margin-bottom: 5px;">API密钥 (可选):</label>
                        <input type="text" id="testApiKey" style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;" placeholder="通常为空">
                    </div>
                    <div>
                        <label for="testModelName" style="display: block; margin-bottom: 5px;">模型名称:</label>
                        <input type="text" id="testModelName" style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;" placeholder="例如: openai/gpt-oss-20b">
                    </div>
                </div>
            </div>

            <div style="margin: 20px 0;">
                <h4>测试消息</h4>
                <div style="margin-bottom: 15px;">
                    <label for="testSystemPrompt" style="display: block; margin-bottom: 5px;">系统提示词:</label>
                    <textarea id="testSystemPrompt" style="width: 100%; height: 60px; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px;">Always answer in rhymes. Today is Thursday</textarea>
                </div>
                <div style="margin-bottom: 15px;">
                    <label for="testUserMessage" style="display: block; margin-bottom: 5px;">用户消息:</label>
                    <textarea id="testUserMessage" style="width: 100%; height: 60px; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px;">What day is it today?</textarea>
                </div>
            </div>

            <div style="margin: 20px 0;">
                <h4>高级参数</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px;">
                    <div>
                        <label for="testTemperature" style="display: block; margin-bottom: 5px;">温度:</label>
                        <input type="number" id="testTemperature" step="0.1" min="0" max="2" style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;" value="0.7">
                    </div>
                    <div>
                        <label for="testMaxTokens" style="display: block; margin-bottom: 5px;">最大令牌数:</label>
                        <input type="number" id="testMaxTokens" style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;" value="-1">
                    </div>
                    <div>
                        <label for="testStream" style="display: block; margin-bottom: 5px;">流式输出:</label>
                        <select id="testStream" style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;">
                            <option value="false">否</option>
                            <option value="true">是</option>
                        </select>
                    </div>
                </div>
            </div>

            <button onclick="testOpenAIAPI()" class="btn btn-primary">🧪 测试API</button>

            <div id="apiTestResult" class="test-result" style="display: none; margin-top: 20px;">
                <h4>API测试结果:</h4>
                <div id="apiTestResponse"></div>
            </div>
        </div>
    </div>

    <script>
        let currentTestModel = null;

        // 页面加载时初始化
        document.addEventListener('DOMContentLoaded', function() {
            refreshStatus();
            refreshModels();
        });

        // 刷新服务器状态
        async function refreshStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();

                const statusCard = document.getElementById('status-card');
                const statusContent = document.getElementById('status-content');

                if (data.connected) {
                    statusCard.className = 'status-card status-connected';
                    statusContent.innerHTML = `
                        <div class="status-grid">
                            <div class="status-item">
                                <div class="value">✅ 已连接</div>
                                <div class="label">连接状态</div>
                            </div>
                            <div class="status-item">
                                <div class="value">${data.host}:${data.port}</div>
                                <div class="label">服务器地址</div>
                            </div>
                            <div class="status-item">
                                <div class="value">${data.available_models_count}</div>
                                <div class="label">可用模型</div>
                            </div>
                            <div class="status-item">
                                <div class="value">${data.response_time.toFixed(2)}s</div>
                                <div class="label">响应时间</div>
                            </div>
                        </div>
                        ${data.current_model ? `<p style="margin-top: 15px; text-align: center;"><strong>当前模型:</strong> ${data.current_model}</p>` : '<p style="margin-top: 15px; text-align: center; color: #6b7280;">未加载模型</p>'}
                    `;
                } else {
                    statusCard.className = 'status-card status-disconnected';
                    statusContent.innerHTML = `
                        <div class="error-message">
                            <strong>❌ 连接失败</strong><br>
                            ${data.error_message || '无法连接到LM Studio服务器'}
                        </div>
                        <div style="margin-top: 15px;">
                            <p>请确保:</p>
                            <ul style="margin-left: 20px; margin-top: 10px;">
                                <li>LM Studio正在运行</li>
                                <li>服务器启动在 ${data.host}:${data.port}</li>
                                <li>已加载至少一个模型</li>
                            </ul>
                        </div>
                    `;
                }
            } catch (error) {
                console.error('刷新状态失败:', error);
                document.getElementById('status-content').innerHTML = `
                    <div class="error-message">
                        <strong>获取状态失败</strong><br>
                        ${error.message}
                    </div>
                `;
            }
        }

        // 刷新模型列表
        async function refreshModels() {
            const container = document.getElementById('models-container');
            container.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>正在刷新模型列表...</p>
                </div>
            `;

            try {
                const response = await fetch('/api/models');
                const data = await response.json();

                if (data.success) {
                    displayModels(data.models, data.current_model);
                } else {
                    throw new Error(data.error || '获取模型列表失败');
                }
            } catch (error) {
                console.error('刷新模型失败:', error);
                container.innerHTML = `
                    <div class="error-message">
                        <strong>加载模型失败</strong><br>
                        ${error.message}
                    </div>
                `;
            }
        }

        // 显示模型列表
        function displayModels(models, currentModelId) {
            const container = document.getElementById('models-container');

            if (!models || models.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #6b7280;">
                        <h3>😔 未发现可用模型</h3>
                        <p>请确保在LM Studio中加载了至少一个模型</p>
                    </div>
                `;
                return;
            }

            const modelsHtml = models.map(model => {
                const isCurrent = model.id === currentModelId;
                const isRecommended = model.recommended;

                return `
                    <div class="model-card ${isCurrent ? 'selected' : ''} ${isRecommended ? 'recommended' : ''}">
                        <div class="model-header">
                            <div>
                                <div class="model-title">${model.name}</div>
                                <div class="model-id">${model.id}</div>
                            </div>
                            ${isRecommended ? '<span class="badge badge-recommended">⭐ 推荐</span>' : ''}
                            ${isCurrent ? '<span class="badge badge-current">📋 当前</span>' : ''}
                        </div>

                        <div class="model-badges">
                            ${model.parameters ? `<span class="badge badge-parameters">${model.parameters}</span>` : ''}
                            ${model.quantization ? `<span class="badge badge-quantization">${model.quantization}</span>` : ''}
                        </div>

                        <div class="model-description">${model.description || '暂无描述'}</div>

                        <div class="model-actions">
                            ${!isCurrent ? `
                                <button onclick="selectModel('${model.id}')" class="btn btn-primary btn-small">
                                    选择
                                </button>
                            ` : '<span style="color: #10b981; font-weight: 500;">✓ 已选择</span>'}

                            <button onclick="openTestModal('${model.id}', '${model.name.replace(/'/g, "\\'")}')" class="btn btn-secondary btn-small">
                                测试
                            </button>

                            <div class="compatibility-score">
                                <span>兼容性:</span>
                                <div class="score-bar">
                                    <div class="score-fill" style="width: ${model.compatibility_score * 20}%"></div>
                                </div>
                                <span>${model.compatibility_score.toFixed(1)}/5.0</span>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            container.innerHTML = `<div class="models-grid">${modelsHtml}</div>`;
        }

        // 选择模型
        async function selectModel(modelId) {
            try {
                showMessage('正在选择模型...', 'info');

                const response = await fetch('/api/select_model', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ model_id: modelId })
                });

                const data = await response.json();

                if (data.success) {
                    showMessage(`✅ 已选择模型: ${modelId}`, 'success');
                    await refreshStatus();
                    await refreshModels();
                } else {
                    throw new Error(data.error || '选择模型失败');
                }
            } catch (error) {
                console.error('选择模型失败:', error);
                showMessage(`❌ 选择模型失败: ${error.message}`, 'error');
            }
        }

        // 获取推荐模型
        async function getRecommendations() {
            try {
                const useCase = document.getElementById('useCase').value;

                const response = await fetch(`/api/recommendations?use_case=${useCase}`);
                const data = await response.json();

                if (data.success) {
                    showMessage(`📝 已为您推荐 ${data.models.length} 个模型`, 'success');
                    displayModels(data.models, data.current_model);
                } else {
                    throw new Error(data.error || '获取推荐失败');
                }
            } catch (error) {
                console.error('获取推荐失败:', error);
                showMessage(`❌ 获取推荐失败: ${error.message}`, 'error');
            }
        }

        // 打开测试对话框
        function openTestModal(modelId, modelName) {
            currentTestModel = modelId;
            document.getElementById('testModelName').textContent = modelName;
            document.getElementById('testResult').style.display = 'none';
            document.getElementById('testModal').style.display = 'block';
        }

        // 关闭测试对话框
        function closeTestModal() {
            document.getElementById('testModal').style.display = 'none';
            currentTestModel = null;
        }

        // 测试模型
        async function testModel() {
            if (!currentTestModel) return;

            const testPrompt = document.getElementById('testPrompt').value;
            const testResult = document.getElementById('testResult');
            const testResponse = document.getElementById('testResponse');

            testResult.style.display = 'block';
            testResponse.innerHTML = '<div class="spinner" style="margin: 20px auto;"></div><p style="text-align: center;">正在测试模型响应...</p>';

            try {
                const response = await fetch('/api/test_model', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        model_id: currentTestModel,
                        prompt: testPrompt
                    })
                });

                const data = await response.json();

                if (data.success) {
                    testResponse.innerHTML = `
                        <div style="margin-bottom: 10px;">
                            <strong>响应时间:</strong> ${data.response_time.toFixed(2)}秒
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>模型响应:</strong>
                        </div>
                        <div class="test-response">${data.response}</div>
                    `;
                } else {
                    throw new Error(data.error || '测试失败');
                }
            } catch (error) {
                console.error('测试模型失败:', error);
                testResponse.innerHTML = `
                    <div class="error-message">
                        <strong>测试失败</strong><br>
                        ${error.message}
                    </div>
                `;
            }
        }

        // 显示消息
        function showMessage(message, type = 'info') {
            const messageArea = document.getElementById('message-area');
            const className = type === 'error' ? 'error-message' :
                            type === 'success' ? 'success-message' : 'info-message';

            messageArea.innerHTML = `<div class="${className}">${message}</div>`;

            // 3秒后自动清除消息
            setTimeout(() => {
                messageArea.innerHTML = '';
            }, 3000);
        }

        // 点击对话框外部关闭
        window.onclick = function(event) {
            const modal = document.getElementById('testModal');
            if (event.target === modal) {
                closeTestModal();
            }
        }

        // 配置对话框功能
        async function openConfigModal() {
            try {
                const response = await fetch('/api/config');
                const data = await response.json();

                if (data.success) {
                    const config = data.config;
                    const lmConfig = config.lm_studio || {};
                    const apiConfig = lmConfig.api || {};
                    const modelConfig = lmConfig.model || {};

                    // 填充表单
                    document.getElementById('apiBaseUrl').value = apiConfig.base_url || 'http://127.0.0.1:1234/v1';
                    document.getElementById('apiKey').value = apiConfig.api_key || '';
                    document.getElementById('preferredModel').value = modelConfig.preferred_model || '';
                    document.getElementById('maxTokens').value = modelConfig.max_tokens || 2048;
                    document.getElementById('temperature').value = modelConfig.temperature || 0.7;
                    document.getElementById('topP').value = modelConfig.top_p || 0.9;

                    // 显示模型映射
                    await loadModelMappings();

                    document.getElementById('configModal').style.display = 'block';
                } else {
                    showMessage('❌ 获取配置失败: ' + data.error, 'error');
                }
            } catch (error) {
                console.error('打开配置对话框失败:', error);
                showMessage('❌ 打开配置失败: ' + error.message, 'error');
            }
        }

        function closeConfigModal() {
            document.getElementById('configModal').style.display = 'none';
        }

        async function loadModelMappings() {
            try {
                const response = await fetch('/api/model_mappings');
                const data = await response.json();

                if (data.success) {
                    const mappings = data.mappings;
                    const container = document.getElementById('modelMappings');

                    if (Object.keys(mappings).length === 0) {
                        container.innerHTML = '<div style="color: #6b7280; text-align: center;">暂无映射</div>';
                    } else {
                        let html = '';
                        for (const [actualId, displayName] of Object.entries(mappings)) {
                            html += `
                                <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px; margin-bottom: 5px; background: #f8fafc; border-radius: 4px;">
                                    <div>
                                        <strong>${actualId}</strong> → ${displayName}
                                    </div>
                                    <button onclick="removeModelMapping('${actualId}')" class="btn btn-secondary btn-small">删除</button>
                                </div>
                            `;
                        }
                        container.innerHTML = html;
                    }
                }
            } catch (error) {
                console.error('加载模型映射失败:', error);
            }
        }

        async function saveConfig() {
            try {
                const config = {
                    lm_studio: {
                        api: {
                            base_url: document.getElementById('apiBaseUrl').value,
                            api_key: document.getElementById('apiKey').value
                        },
                        model: {
                            preferred_model: document.getElementById('preferredModel').value,
                            max_tokens: parseInt(document.getElementById('maxTokens').value),
                            temperature: parseFloat(document.getElementById('temperature').value),
                            top_p: parseFloat(document.getElementById('topP').value)
                        }
                    }
                };

                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(config)
                });

                const data = await response.json();
                const resultDiv = document.getElementById('configResult');
                const responseDiv = document.getElementById('configResponse');

                resultDiv.style.display = 'block';

                if (data.success) {
                    responseDiv.innerHTML = `<div class="success-message">${data.message}</div>`;
                    showMessage('✅ 配置保存成功', 'success');

                    // 刷新状态和模型列表
                    await refreshStatus();
                    await refreshModels();

                    setTimeout(() => {
                        closeConfigModal();
                    }, 2000);
                } else {
                    responseDiv.innerHTML = `<div class="error-message">保存失败: ${data.error}</div>`;
                }
            } catch (error) {
                console.error('保存配置失败:', error);
                document.getElementById('configResult').style.display = 'block';
                document.getElementById('configResponse').innerHTML = `<div class="error-message">保存失败: ${error.message}</div>`;
            }
        }

        async function addModelMapping() {
            const actualId = document.getElementById('newMappingId').value.trim();
            const displayName = document.getElementById('newMappingName').value.trim();

            if (!actualId || !displayName) {
                showMessage('❌ 请填写完整的映射信息', 'error');
                return;
            }

            try {
                const response = await fetch('/api/add_model_mapping', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        actual_model_id: actualId,
                        display_name: displayName
                    })
                });

                const data = await response.json();

                if (data.success) {
                    showMessage('✅ ' + data.message, 'success');
                    document.getElementById('newMappingId').value = '';
                    document.getElementById('newMappingName').value = '';
                    await loadModelMappings();
                } else {
                    showMessage('❌ 添加映射失败: ' + data.error, 'error');
                }
            } catch (error) {
                console.error('添加模型映射失败:', error);
                showMessage('❌ 添加映射失败: ' + error.message, 'error');
            }
        }

        async function removeModelMapping(actualId) {
            if (!confirm(`确定要删除模型映射 "${actualId}" 吗？`)) {
                return;
            }

            try {
                const response = await fetch('/api/remove_model_mapping', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        actual_model_id: actualId
                    })
                });

                const data = await response.json();

                if (data.success) {
                    showMessage('✅ ' + data.message, 'success');
                    await loadModelMappings();
                } else {
                    showMessage('❌ 删除映射失败: ' + data.error, 'error');
                }
            } catch (error) {
                console.error('删除模型映射失败:', error);
                showMessage('❌ 删除映射失败: ' + error.message, 'error');
            }
        }

        // API测试对话框功能
        function openAPITestModal() {
            document.getElementById('apiTestModal').style.display = 'block';
        }

        function closeAPITestModal() {
            document.getElementById('apiTestModal').style.display = 'none';
        }

        async function testOpenAIAPI() {
            const apiUrl = document.getElementById('testApiUrl').value.trim();
            const apiKey = document.getElementById('testApiKey').value.trim();
            const modelName = document.getElementById('testModelName').value.trim();
            const systemPrompt = document.getElementById('testSystemPrompt').value.trim();
            const userMessage = document.getElementById('testUserMessage').value.trim();

            if (!apiUrl || !modelName || !systemPrompt || !userMessage) {
                showMessage('❌ 请填写完整的API测试信息', 'error');
                return;
            }

            const resultDiv = document.getElementById('apiTestResult');
            const responseDiv = document.getElementById('apiTestResponse');

            resultDiv.style.display = 'block';
            responseDiv.innerHTML = '<div class="spinner" style="margin: 20px auto;"></div><p style="text-align: center;">正在测试API...</p>';

            try {
                const requestData = {
                    api_url: apiUrl,
                    api_key: apiKey,
                    model_name: modelName,
                    test_message: userMessage,
                    system_prompt: systemPrompt,
                    temperature: parseFloat(document.getElementById('testTemperature').value),
                    max_tokens: parseInt(document.getElementById('testMaxTokens').value),
                    stream: document.getElementById('testStream').value === 'true'
                };

                const response = await fetch('/api/test_openai_api', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestData)
                });

                const data = await response.json();

                if (data.success) {
                    let html = `
                        <div style="margin-bottom: 15px;">
                            <strong>✅ API测试成功</strong>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                            <div><strong>响应时间:</strong> ${data.response_time.toFixed(2)}秒</div>
                            <div><strong>状态码:</strong> ${data.status_code}</div>
                            <div><strong>使用模型:</strong> ${data.model_used}</div>
                            <div><strong>令牌使用:</strong> ${data.usage.total_tokens || 'N/A'}</div>
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>API响应:</strong>
                        </div>
                        <div class="test-response">${data.response}</div>
                    `;
                    responseDiv.innerHTML = html;
                    showMessage('✅ API测试成功', 'success');
                } else {
                    let html = `
                        <div class="error-message">
                            <strong>❌ API测试失败</strong><br>
                            错误: ${data.error}<br>
                            状态码: ${data.status_code}<br>
                            响应时间: ${data.response_time ? data.response_time.toFixed(2) + '秒' : 'N/A'}
                        </div>
                    `;
                    if (data.response_text) {
                        html += `
                            <div style="margin-top: 10px;">
                                <strong>原始响应:</strong>
                                <div class="test-response" style="max-height: 200px;">${data.response_text}</div>
                            </div>
                        `;
                    }
                    responseDiv.innerHTML = html;
                    showMessage('❌ API测试失败', 'error');
                }
            } catch (error) {
                console.error('API测试失败:', error);
                responseDiv.innerHTML = `
                    <div class="error-message">
                        <strong>测试异常</strong><br>
                        ${error.message}
                    </div>
                `;
                showMessage('❌ API测试异常: ' + error.message, 'error');
            }
        }

        // 定期刷新状态
        setInterval(refreshStatus, 30000); // 每30秒刷新一次状态
    </script>
</body>
</html>
"""

@app.route('/')
def model_management_page():
    """模型管理页面"""
    return render_template_string(MODEL_MANAGEMENT_PAGE)

@app.route('/api/status', methods=['GET'])
def get_server_status():
    """获取服务器状态"""
    try:
        status = model_manager.get_server_status()
        return jsonify({
            "success": True,
            "status": asdict(status)
        })
    except Exception as e:
        logger.error(f"获取服务器状态失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/models', methods=['GET'])
def get_models():
    """获取模型列表"""
    try:
        models = model_manager.refresh_models()
        current_model = model_manager.get_current_model()
        current_model_id = current_model.id if current_model else None

        return jsonify({
            "success": True,
            "models": [asdict(model) for model in models],
            "current_model": current_model_id,
            "total_count": len(models)
        })
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/refresh_models', methods=['POST'])
def refresh_models():
    """刷新模型列表"""
    try:
        force_refresh = request.json.get('force_refresh', True) if request.json else True
        models = model_manager.refresh_models(force_refresh=force_refresh)

        return jsonify({
            "success": True,
            "models": [asdict(model) for model in models],
            "refreshed_at": model_manager._last_refresh_time
        })
    except Exception as e:
        logger.error(f"刷新模型列表失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/select_model', methods=['POST'])
def select_model():
    """选择模型"""
    try:
        data = request.get_json()
        if not data or 'model_id' not in data:
            return jsonify({
                "success": False,
                "error": "缺少model_id参数"
            }), 400

        model_id = data['model_id']
        success = model_manager.select_model(model_id)

        if success:
            return jsonify({
                "success": True,
                "message": f"已选择模型: {model_id}",
                "model_id": model_id
            })
        else:
            return jsonify({
                "success": False,
                "error": "选择模型失败"
            }), 500

    except Exception as e:
        logger.error(f"选择模型失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/test_model', methods=['POST'])
def test_model():
    """测试模型"""
    try:
        data = request.get_json()
        if not data or 'model_id' not in data:
            return jsonify({
                "success": False,
                "error": "缺少model_id参数"
            }), 400

        model_id = data['model_id']
        test_prompt = data.get('prompt', '你好，请简单介绍一下自己。')

        result = model_manager.test_model(model_id, test_prompt)

        if result['success']:
            return jsonify(result)
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', '测试失败')
            }), 500

    except Exception as e:
        logger.error(f"测试模型失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    """获取模型推荐"""
    try:
        use_case = request.args.get('use_case', 'general')
        models = model_manager.get_model_recommendations(use_case)
        current_model = model_manager.get_current_model()
        current_model_id = current_model.id if current_model else None

        return jsonify({
            "success": True,
            "models": [asdict(model) for model in models],
            "current_model": current_model_id,
            "use_case": use_case
        })
    except Exception as e:
        logger.error(f"获取推荐失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/current_model', methods=['GET'])
def get_current_model():
    """获取当前选中的模型"""
    try:
        model = model_manager.get_current_model()

        if model:
            return jsonify({
                "success": True,
                "model": asdict(model)
            })
        else:
            return jsonify({
                "success": True,
                "model": None,
                "message": "未选择模型"
            })
    except Exception as e:
        logger.error(f"获取当前模型失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/export_models', methods=['GET'])
def export_models():
    """导出模型列表"""
    try:
        format_type = request.args.get('format', 'json').lower()

        if format_type not in ['json', 'csv']:
            return jsonify({
                "success": False,
                "error": "不支持的导出格式，支持: json, csv"
            }), 400

        export_data = model_manager.export_model_list(format_type)

        if format_type == 'json':
            return export_data, 200, {'Content-Type': 'application/json; charset=utf-8'}
        else:  # csv
            return export_data, 200, {'Content-Type': 'text/csv; charset=utf-8'}

    except Exception as e:
        logger.error(f"导出模型列表失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/config', methods=['GET'])
def get_ai_config():
    """获取AI配置"""
    try:
        config = config_manager.get_full_config()
        return jsonify({
            "success": True,
            "config": config
        })
    except Exception as e:
        logger.error(f"获取AI配置失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/config', methods=['POST'])
def update_ai_config():
    """更新AI配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求数据为空"
            }), 400

        # 更新LM Studio配置
        if 'lm_studio' in data:
            lm_config = data['lm_studio']
            current_config = config_manager.config.get('lm_studio', {})

            # 更新API配置
            if 'api' in lm_config:
                if 'api' not in current_config:
                    current_config['api'] = {}
                current_config['api'].update(lm_config['api'])

            # 更新模型配置
            if 'model' in lm_config:
                if 'model' not in current_config:
                    current_config['model'] = {}
                current_config['model'].update(lm_config['model'])

            # 更新基本配置
            for key in ['host', 'port', 'timeout', 'retry_attempts', 'retry_delay']:
                if key in lm_config:
                    current_config[key] = lm_config[key]

            config_manager.config['lm_studio'] = current_config

        # 保存配置
        if config_manager.save_config():
            # 重置连接器以使用新配置
            reset_model_manager()

            return jsonify({
                "success": True,
                "message": "配置更新成功"
            })
        else:
            return jsonify({
                "success": False,
                "error": "保存配置失败"
            }), 500

    except Exception as e:
        logger.error(f"更新AI配置失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/test_openai_api', methods=['POST'])
def test_openai_api():
    """测试OpenAI兼容API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求数据为空"
            }), 400

        # 获取测试参数
        api_url = data.get('api_url', 'http://127.0.0.1:1234/v1/chat/completions')
        api_key = data.get('api_key', '')
        model_name = data.get('model_name', '')
        test_message = data.get('test_message', '你好，请简单介绍一下自己。')

        # 准备请求头
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'SSlogs-AI/1.0'
        }

        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'

        # 准备请求载荷
        messages = [
            {
                "role": "system",
                "content": data.get('system_prompt', '你是一个有用的AI助手。')
            },
            {
                "role": "user",
                "content": test_message
            }
        ]

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": data.get('temperature', 0.7),
            "max_tokens": data.get('max_tokens', 500),
            "stream": data.get('stream', False)
        }

        # 发送请求
        start_time = time.time()
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        response_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            ai_response = result.get('choices', [{}])[0].get('message', {}).get('content', '')

            return jsonify({
                "success": True,
                "response": ai_response,
                "response_time": response_time,
                "model_used": model_name,
                "status_code": response.status_code,
                "usage": result.get('usage', {})
            })
        else:
            return jsonify({
                "success": False,
                "error": f"API请求失败: HTTP {response.status_code}",
                "response_text": response.text,
                "response_time": response_time,
                "status_code": response.status_code
            })

    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "error": "请求超时，请检查API地址和网络连接"
        }), 500
    except requests.exceptions.ConnectionError:
        return jsonify({
            "success": False,
            "error": "无法连接到API服务器，请检查地址和端口"
        }), 500
    except Exception as e:
        logger.error(f"测试OpenAI API失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/add_model_mapping', methods=['POST'])
def add_model_mapping():
    """添加模型名称映射"""
    try:
        data = request.get_json()
        if not data or 'actual_model_id' not in data or 'display_name' not in data:
            return jsonify({
                "success": False,
                "error": "缺少actual_model_id或display_name参数"
            }), 400

        actual_model_id = data['actual_model_id']
        display_name = data['display_name']

        # 获取当前配置
        config = config_manager.get_full_config()
        lm_config = config.setdefault('lm_studio', {})
        model_config = lm_config.setdefault('model', {})
        model_mapping = model_config.setdefault('model_mapping', {})

        # 添加映射
        model_mapping[actual_model_id] = display_name

        # 保存配置
        if config_manager.save_config():
            # 重置模型管理器
            reset_model_manager()

            return jsonify({
                "success": True,
                "message": f"已添加模型映射: {actual_model_id} -> {display_name}"
            })
        else:
            return jsonify({
                "success": False,
                "error": "保存配置失败"
            }), 500

    except Exception as e:
        logger.error(f"添加模型映射失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/remove_model_mapping', methods=['POST'])
def remove_model_mapping():
    """删除模型名称映射"""
    try:
        data = request.get_json()
        if not data or 'actual_model_id' not in data:
            return jsonify({
                "success": False,
                "error": "缺少actual_model_id参数"
            }), 400

        actual_model_id = data['actual_model_id']

        # 获取当前配置
        config = config_manager.get_full_config()
        lm_config = config.get('lm_studio', {})
        model_config = lm_config.get('model', {})
        model_mapping = model_config.get('model_mapping', {})

        # 删除映射
        if actual_model_id in model_mapping:
            del model_mapping[actual_model_id]

            # 保存配置
            if config_manager.save_config():
                # 重置模型管理器
                reset_model_manager()

                return jsonify({
                    "success": True,
                    "message": f"已删除模型映射: {actual_model_id}"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "保存配置失败"
                }), 500
        else:
            return jsonify({
                "success": False,
                "error": f"模型映射不存在: {actual_model_id}"
            }), 404

    except Exception as e:
        logger.error(f"删除模型映射失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/model_mappings', methods=['GET'])
def get_model_mappings():
    """获取模型名称映射"""
    try:
        config = config_manager.get_full_config()
        lm_config = config.get('lm_studio', {})
        model_config = lm_config.get('model', {})
        model_mapping = model_config.get('model_mapping', {})

        return jsonify({
            "success": True,
            "mappings": model_mapping
        })

    except Exception as e:
        logger.error(f"获取模型映射失败: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def create_model_management_server(host: str = "127.0.0.1", port: int = 8080, debug: bool = False):
    """创建模型管理服务器"""

    def run_server():
        logger.info(f"启动模型管理服务器: http://{host}:{port}")
        app.run(host=host, port=port, debug=debug, threaded=True)

    return run_server

if __name__ == "__main__":
    # 直接运行时启动服务器
    logger.info("启动SSlogs AI模型管理服务器...")
    create_model_management_server(debug=True)()