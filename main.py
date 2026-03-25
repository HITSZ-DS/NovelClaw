# 桌面端启动器与管理界面入口 (Desktop Launcher and Management UI Entry)
# 该文件负责启动 CoLong Idea Studio 桌面端应用，提供用户界面和操作入口。
# (This file is responsible for launching the CoLong Idea Studio desktop application, providing the user interface and operation entry points.)
# 包含启动器主窗口、设置界面、自定义 Provider 管理等功能。
# (Includes the launcher main window, settings interface, custom Provider management, and other features.)
# 制作 (Created by)：sirvffg冷月笙寒
# 网站 (Website)：https://lygalaxy.cn

import sys
import os
import subprocess
import threading
from PySide6.QtCore import Qt, QThread, Signal, QRect
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel
from PySide6.QtGui import QIcon, QFont, QColor
from qfluentwidgets import (
    MSFluentWindow, 
    SubtitleLabel, 
    BodyLabel, 
    PrimaryPushButton, 
    PushButton,
    TextEdit,
    CardWidget,
    setTheme,
    Theme,
    FluentIcon,
    MessageBox,
    TableWidget,
    Action,
    SpinBox,
    NavigationItemPosition,
    LineEdit,
    ComboBox,
    SingleDirectionScrollArea
)

import sqlite3
import json

# ==========================================
# 国际化 (i18n) 简易实现
# ==========================================
class I18n:
    def __init__(self):
        self.lang = "zh_CN"
        self.translations = {
            "zh_CN": {
                "window_title": "CoLong Idea Studio",
                "nav_launch": "启动中心",
                "nav_user": "用户管理",
                "nav_provider": "Provider管理",
                "nav_db": "数据库管理",
                "nav_settings": "系统设置",
                
                # Provider Management
                "provider_title": "自定义 Provider 管理",
                "provider_subtitle": "添加你自己的 Provider，支持自定义 Base URL、Model 和请求模式。",
                "provider_slug_label": "Provider 标识",
                "provider_slug_ph": "例如：moonshot (仅支持 a-z / 0-9 / _ / -)",
                "provider_name_label": "显示名称 (可选)",
                "provider_name_ph": "例如：MOONSHOT (可选)",
                "provider_base_label": "Base URL",
                "provider_base_ph": "例如：https://api.example.com/v1",
                "provider_model_label": "Model",
                "provider_model_ph": "例如：model-name",
                "provider_mode_label": "请求模式",
                "provider_save_btn": "保存自定义 Provider",
                "provider_list_title": "已保存的 Provider",
                "provider_empty": "还没有自定义 Provider。",
                "provider_refresh": "刷新",
                "provider_table_src": "来源",
                "provider_table_slug": "标识",
                "provider_table_name": "名称",
                "provider_table_base": "Base URL",
                "provider_table_model": "Model",
                "provider_table_mode": "请求模式",
                "provider_ctx_del": "删除此 Provider",
                "provider_err_empty": "标识、Base URL 和 Model 不能为空！",
                "provider_err_format": "Provider 标识格式不正确！(需满足 a-z / 0-9 / _ / -)",
                "provider_err_exist_global": "标识 '{slug}' 已经存在于全局配置中！",
                "provider_save_success": "自定义 Provider 保存成功！重启网页端后生效。",
                "provider_del_db_confirm": "确定要从数据库中删除用户配置的 Provider '{slug}' 吗？",
                "provider_del_global_confirm": "确定要从全局配置文件中删除 Provider '{slug}' 吗？",
                "provider_del_db_success": "已成功从数据库删除。",
                "provider_del_global_success": "已成功从全局配置文件删除，重启网页端后生效。",
                "provider_err": "错误",
                "provider_success": "成功",
                "provider_del_fail": "删除失败",
                "provider_save_fail": "保存失败",
                "provider_src_global": "全局 (文件)",
                "provider_src_user": "用户 (ID:{id})",
                "provider_src_unknown": "未知",

                # Settings
                "setting_title": "系统设置",
                "setting_port_title": "网页端服务端口",
                "setting_port_desc": "设置本地网页版启动时使用的端口号。默认: 8010",
                "setting_lang_title": "界面语言 (Language)",
                "setting_lang_desc": "设置启动器界面的显示语言。重启后完全生效。",
                "setting_save": "保存",
                "setting_save_success": "保存成功",
                "setting_save_msg": "设置已保存。下次启动生效。",
                "setting_save_fail": "保存失败",

                # User Management
                "user_title": "用户管理",
                "user_refresh": "刷新",
                "user_desc": "查看和管理网页端的注册用户。您可以右键点击用户进行删除。",
                "user_table_id": "ID",
                "user_table_email": "邮箱 (Email)",
                "user_table_time": "注册时间 (Created At)",
                "user_no_db": "未找到数据库 (app.db)，可能还未有用户注册。",
                "user_count": "共找到 {count} 个用户。",
                "user_no_table": "数据库中暂无用户表。",
                "user_ctx_del": "删除用户",
                "user_del_confirm_title": "确认删除",
                "user_del_confirm_msg": "确定要删除用户 '{username}' 吗？\n删除后不可恢复！",
                "user_del_success": "用户 '{username}' 已被删除。",

                # Database Management
                "db_title": "数据库与缓存管理",
                "db_web_title": "清理网页端数据库 (app.db)",
                "db_web_desc": "删除网页端所有的用户、任务记录。请在服务停止时操作。",
                "db_vector_title": "清理向量数据库 (vector_db/)",
                "db_vector_desc": "清空记忆库和 RAG 索引数据。将重置 AI 的记忆。",
                "db_runs_title": "清理历史生成日志 (runs/)",
                "db_runs_desc": "删除所有生成的文本结果、进度日志和缓存文件。",
                "db_clear_btn": "清理",
                "db_confirm_title": "确认清理？",
                "db_web_confirm": "这将删除网页端所有的任务和账号数据，不可恢复！",
                "db_vector_confirm": "这将清空向量数据库，导致 AI 失去所有动态记忆！",
                "db_runs_confirm": "这将删除所有的历史运行结果和长文本文件！",
                "db_clear_success": "清理成功",
                "db_clear_success_msg": "成功清理了 {target}",
                "db_clear_none": "提示",
                "db_clear_none_msg": "目标不存在，无需清理",
                "db_clear_fail": "清理失败",

                # Init Wizard
                "init_title": "环境初始化向导",
                "init_step1": "1. 创建 .env 虚拟环境:",
                "init_step2": "2. 进入 env 环境 (配置路径):",
                "init_step3": "3. 安装依赖扩展:",
                "init_wait": "等待中...",
                "init_doing": "进行中...",
                "init_fail": "失败",
                "init_done": "已完成",
                "init_start_btn": "开始初始化",
                "init_log_start": ">>> 开始执行初始化流程...",

                # Main Launcher
                "main_title": "启动中心",
                "main_start_btn": "▶ 启动网页版",
                "main_open_btn": "🌐 访问网页",
                "main_stop_btn": "⏹ 停止运行",
                "main_term_title": "虚拟终端输出:",
                "main_welcome": "欢迎使用 CoLong Idea Studio 启动中心！\n请点击上方按钮启动。\n",
                "main_stopping": "\n[系统] 正在停止服务...\n",
                "main_stop_err": "[系统] 停止服务时出错: {err}\n",
                "main_stopped": "[系统] 服务已停止。\n",
                "main_starting": "\n==================================================\n[系统] 准备启动 网页版 (Web Portal) 端口: {port}...\n",
                "main_visit": "👉 请在浏览器中访问: http://127.0.0.1:{port}\n\n",
                "main_start_err": "[错误] 启动失败: {err}\n",
                
                # Exit Confirm
                "exit_confirm_title": "确认退出",
                "exit_confirm_msg": "当前有网页服务正在运行，退出启动器将同时停止该服务。\n\n您确定要退出吗？"
            },
            "en_US": {
                "window_title": "CoLong Idea Studio",
                "nav_launch": "Launcher",
                "nav_user": "Users",
                "nav_provider": "Providers",
                "nav_db": "Database",
                "nav_settings": "Settings",
                
                # Provider Management
                "provider_title": "Custom Provider Management",
                "provider_subtitle": "Add your own Provider with custom Base URL, Model, and request mode.",
                "provider_slug_label": "Provider Slug",
                "provider_slug_ph": "e.g. moonshot (a-z / 0-9 / _ / - only)",
                "provider_name_label": "Display Name (Optional)",
                "provider_name_ph": "e.g. MOONSHOT (Optional)",
                "provider_base_label": "Base URL",
                "provider_base_ph": "e.g. https://api.example.com/v1",
                "provider_model_label": "Model",
                "provider_model_ph": "e.g. model-name",
                "provider_mode_label": "Request Mode",
                "provider_save_btn": "Save Custom Provider",
                "provider_list_title": "Saved Providers",
                "provider_empty": "No custom providers yet.",
                "provider_refresh": "Refresh",
                "provider_table_src": "Source",
                "provider_table_slug": "Slug",
                "provider_table_name": "Name",
                "provider_table_base": "Base URL",
                "provider_table_model": "Model",
                "provider_table_mode": "Mode",
                "provider_ctx_del": "Delete this Provider",
                "provider_err_empty": "Slug, Base URL, and Model cannot be empty!",
                "provider_err_format": "Invalid Provider Slug format! (Must be a-z / 0-9 / _ / -)",
                "provider_err_exist_global": "Slug '{slug}' already exists in global config!",
                "provider_save_success": "Custom Provider saved! Restart web portal to take effect.",
                "provider_del_db_confirm": "Are you sure you want to delete user provider '{slug}' from database?",
                "provider_del_global_confirm": "Are you sure you want to delete Provider '{slug}' from global config?",
                "provider_del_db_success": "Successfully deleted from database.",
                "provider_del_global_success": "Successfully deleted from global config, restart web portal to take effect.",
                "provider_err": "Error",
                "provider_success": "Success",
                "provider_del_fail": "Delete Failed",
                "provider_save_fail": "Save Failed",
                "provider_src_global": "Global (File)",
                "provider_src_user": "User (ID:{id})",
                "provider_src_unknown": "Unknown",

                # Settings
                "setting_title": "System Settings",
                "setting_port_title": "Web Portal Port",
                "setting_port_desc": "Set the port number for the local web portal. Default: 8010",
                "setting_lang_title": "Language",
                "setting_lang_desc": "Set the display language of the launcher. Takes full effect after restart.",
                "setting_save": "Save",
                "setting_save_success": "Saved Successfully",
                "setting_save_msg": "Settings saved. Takes effect on next start.",
                "setting_save_fail": "Save Failed",

                # User Management
                "user_title": "User Management",
                "user_refresh": "Refresh",
                "user_desc": "View and manage registered users of the web portal. Right-click to delete.",
                "user_table_id": "ID",
                "user_table_email": "Email",
                "user_table_time": "Created At",
                "user_no_db": "Database (app.db) not found, maybe no users registered yet.",
                "user_count": "Found {count} user(s).",
                "user_no_table": "No users table in database yet.",
                "user_ctx_del": "Delete User",
                "user_del_confirm_title": "Confirm Delete",
                "user_del_confirm_msg": "Are you sure you want to delete user '{username}'?\nThis cannot be undone!",
                "user_del_success": "User '{username}' has been deleted.",

                # Database Management
                "db_title": "Database & Cache Management",
                "db_web_title": "Clear Web Database (app.db)",
                "db_web_desc": "Delete all users and task records. Please do this when service is stopped.",
                "db_vector_title": "Clear Vector Database (vector_db/)",
                "db_vector_desc": "Empty memory base and RAG index. Resets AI's memory.",
                "db_runs_title": "Clear Generation Logs (runs/)",
                "db_runs_desc": "Delete all generated texts, progress logs, and cache files.",
                "db_clear_btn": "Clear",
                "db_confirm_title": "Confirm Clear?",
                "db_web_confirm": "This will delete ALL web tasks and account data, unrecoverable!",
                "db_vector_confirm": "This will empty vector DB, AI will lose all dynamic memory!",
                "db_runs_confirm": "This will delete ALL historical run results and long texts!",
                "db_clear_success": "Clear Success",
                "db_clear_success_msg": "Successfully cleared {target}",
                "db_clear_none": "Info",
                "db_clear_none_msg": "Target does not exist, nothing to clear.",
                "db_clear_fail": "Clear Failed",

                # Init Wizard
                "init_title": "Environment Initialization Wizard",
                "init_step1": "1. Create .env virtual environment:",
                "init_step2": "2. Enter env & configure path:",
                "init_step3": "3. Install dependencies:",
                "init_wait": "Waiting...",
                "init_doing": "In Progress...",
                "init_fail": "Failed",
                "init_done": "Completed",
                "init_start_btn": "Start Initialization",
                "init_log_start": ">>> Starting initialization process...",

                # Main Launcher
                "main_title": "Launcher",
                "main_start_btn": "▶ Start Web Portal",
                "main_open_btn": "🌐 Open in Browser",
                "main_stop_btn": "⏹ Stop",
                "main_term_title": "Virtual Terminal Output:",
                "main_welcome": "Welcome to CoLong Idea Studio Launcher!\nClick the button above to start.\n",
                "main_stopping": "\n[System] Stopping service...\n",
                "main_stop_err": "[System] Error stopping service: {err}\n",
                "main_stopped": "[System] Service stopped.\n",
                "main_starting": "\n==================================================\n[System] Preparing to start Web Portal on port: {port}...\n",
                "main_visit": "👉 Please visit in browser: http://127.0.0.1:{port}\n\n",
                "main_start_err": "[Error] Failed to start: {err}\n",
                
                # Exit Confirm
                "exit_confirm_title": "Confirm Exit",
                "exit_confirm_msg": "Web service is currently running. Exiting the launcher will stop the service.\n\nAre you sure you want to exit?"
            }
        }
        self.load_lang()

    def load_lang(self):
        config_path = os.path.join("local_web_portal", "launcher_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.lang = config.get("lang", "zh_CN")
            except:
                pass
                
    def set_lang(self, lang):
        self.lang = lang
        config_path = os.path.join("local_web_portal", "launcher_config.json")
        config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except:
                pass
        config["lang"] = lang
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except:
            pass

    def t(self, key, **kwargs):
        text = self.translations.get(self.lang, self.translations["zh_CN"]).get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except:
                pass
        return text

i18n = I18n()
# ==========================================

class ProviderManagementWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        
        self.scrollArea = SingleDirectionScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.contentWidget = QWidget()
        self.contentWidget.setStyleSheet("QWidget { background-color: transparent; }")
        self.vBoxLayout = QVBoxLayout(self.contentWidget)
        self.vBoxLayout.setContentsMargins(40, 50, 40, 40)
        self.vBoxLayout.setSpacing(20)

        # 标题
        self.titleLabel = SubtitleLabel(i18n.t("provider_title"), self.contentWidget)
        self.vBoxLayout.addWidget(self.titleLabel)

        self.infoLabel = BodyLabel(i18n.t("provider_subtitle"), self.contentWidget)
        self.infoLabel.setTextColor(QColor(128, 128, 128), QColor(128, 128, 128))
        self.vBoxLayout.addWidget(self.infoLabel)

        # 表单卡片
        self.formCard = CardWidget(self.contentWidget)
        self.formLayout = QVBoxLayout(self.formCard)
        self.formLayout.setContentsMargins(20, 20, 20, 20)
        self.formLayout.setSpacing(15)

        # Provider 标识
        self.slugInput = LineEdit(self.formCard)
        self.slugInput.setPlaceholderText(i18n.t("provider_slug_ph"))
        self.formLayout.addWidget(BodyLabel(i18n.t("provider_slug_label"), self.formCard))
        self.formLayout.addWidget(self.slugInput)

        # 显示名称
        self.labelInput = LineEdit(self.formCard)
        self.labelInput.setPlaceholderText(i18n.t("provider_name_ph"))
        self.formLayout.addWidget(BodyLabel(i18n.t("provider_name_label"), self.formCard))
        self.formLayout.addWidget(self.labelInput)

        # Base URL
        self.baseUrlInput = LineEdit(self.formCard)
        self.baseUrlInput.setPlaceholderText(i18n.t("provider_base_ph"))
        self.formLayout.addWidget(BodyLabel(i18n.t("provider_base_label"), self.formCard))
        self.formLayout.addWidget(self.baseUrlInput)

        # Model
        self.modelInput = LineEdit(self.formCard)
        self.modelInput.setPlaceholderText(i18n.t("provider_model_ph"))
        self.formLayout.addWidget(BodyLabel(i18n.t("provider_model_label"), self.formCard))
        self.formLayout.addWidget(self.modelInput)

        # 请求模式
        self.modeCombo = ComboBox(self.formCard)
        self.modeCombo.addItems(["chat", "responses"])
        self.modeCombo.setCurrentIndex(0)
        self.formLayout.addWidget(BodyLabel(i18n.t("provider_mode_label"), self.formCard))
        self.formLayout.addWidget(self.modeCombo)

        # 保存按钮
        self.saveBtn = PrimaryPushButton(i18n.t("provider_save_btn"), self.formCard)
        self.saveBtn.clicked.connect(self.save_provider)
        self.formLayout.addWidget(self.saveBtn)

        self.vBoxLayout.addWidget(self.formCard)

        # 列表显示区
        self.listHeaderLayout = QHBoxLayout()
        self.listLabel = SubtitleLabel(i18n.t("provider_list_title"), self.contentWidget)
        self.listHeaderLayout.addWidget(self.listLabel)
        
        self.listHeaderLayout.addStretch(1)
        self.refreshBtn = PushButton(FluentIcon.SYNC, i18n.t("provider_refresh"), self.contentWidget)
        self.refreshBtn.clicked.connect(self.load_providers)
        self.listHeaderLayout.addWidget(self.refreshBtn)
        
        self.vBoxLayout.addLayout(self.listHeaderLayout)
        
        self.emptyLabel = BodyLabel(i18n.t("provider_empty"), self.contentWidget)
        self.emptyLabel.setTextColor(QColor(128, 128, 128), QColor(128, 128, 128))
        self.vBoxLayout.addWidget(self.emptyLabel)

        self.tableCard = CardWidget(self.contentWidget)
        self.tableLayout = QVBoxLayout(self.tableCard)
        self.tableLayout.setContentsMargins(10, 10, 10, 10)
        
        self.table = TableWidget(self.tableCard)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            i18n.t("provider_table_src"), 
            i18n.t("provider_table_slug"), 
            i18n.t("provider_table_name"), 
            i18n.t("provider_table_base"), 
            i18n.t("provider_table_model"), 
            i18n.t("provider_table_mode")
        ])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(TableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        # 限制表格最小高度以防止被压缩到不可见
        self.table.setMinimumHeight(200)
        self.tableLayout.addWidget(self.table)
        
        self.tableCard.hide()
        self.vBoxLayout.addWidget(self.tableCard, 1)
        
        self.vBoxLayout.addStretch(1)
        self.scrollArea.setWidget(self.contentWidget)
        self.mainLayout.addWidget(self.scrollArea)

        # 右键菜单
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        self.providers_path = os.path.join("local_web_portal", "custom_providers.json")
        self.db_path = os.path.join("local_web_portal", "data", "app.db")
        self.load_providers()

    def load_providers(self):
        self.providers = []
        # 1. 从 custom_providers.json 中读取 (全局配置)
        if os.path.exists(self.providers_path):
            try:
                # 尝试用 utf-8 读，不行再尝试其他编码（比如 utf-16 等由于之前可能错误写入导致的编码）
                try:
                    with open(self.providers_path, 'r', encoding='utf-8') as f:
                        file_providers = json.load(f)
                except UnicodeDecodeError:
                    with open(self.providers_path, 'r', encoding='utf-16') as f:
                        file_providers = json.load(f)
                for p in file_providers:
                    p["source"] = i18n.t("provider_src_global")
                    self.providers.append(p)
            except Exception as e:
                print(f"Error loading file providers: {e}")
                pass

        # 2. 从 app.db 数据库中读取 (用户配置)
        if os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                # 从 users 表关联读取 username/email，这里简化只读取 provider_configs
                cursor.execute("SELECT slug, label, base_url, model, wire_api, user_id FROM provider_configs")
                db_rows = cursor.fetchall()
                for row in db_rows:
                    self.providers.append({
                        "slug": row[0],
                        "label": row[1],
                        "base_url": row[2],
                        "model": row[3],
                        "wire_api": row[4],
                        "source": i18n.t("provider_src_user", id=row[5]),
                        "is_db": True
                    })
                conn.close()
            except Exception as e:
                print(f"Error loading db providers: {e}")
                pass

        if not self.providers:
            self.emptyLabel.show()
            self.tableCard.hide()
        else:
            self.emptyLabel.hide()
            self.tableCard.show()
            self.table.setRowCount(len(self.providers))
            from PySide6.QtWidgets import QTableWidgetItem
            for row_idx, p in enumerate(self.providers):
                self.table.setItem(row_idx, 0, QTableWidgetItem(p.get("source", i18n.t("provider_src_unknown"))))
                self.table.setItem(row_idx, 1, QTableWidgetItem(p.get("slug", "")))
                self.table.setItem(row_idx, 2, QTableWidgetItem(p.get("label", "")))
                self.table.setItem(row_idx, 3, QTableWidgetItem(p.get("base_url", "")))
                self.table.setItem(row_idx, 4, QTableWidgetItem(p.get("model", "")))
                self.table.setItem(row_idx, 5, QTableWidgetItem(p.get("wire_api", "")))

    def save_provider(self):
        slug = self.slugInput.text().strip()
        label = self.labelInput.text().strip()
        base_url = self.baseUrlInput.text().strip()
        model = self.modelInput.text().strip()
        wire_api = self.modeCombo.currentText()
        
        if not slug or not base_url or not model:
            MessageBox(i18n.t("provider_err"), i18n.t("provider_err_empty"), self.window()).exec()
            return
            
        import re
        if not re.match(r"^[a-z0-9][a-z0-9_-]{1,31}$", slug):
            MessageBox(i18n.t("provider_err"), i18n.t("provider_err_format"), self.window()).exec()
            return
            
        # 检查是否已存在于全局文件中
        file_providers = [p for p in self.providers if not p.get("is_db", False)]
        for p in file_providers:
            if p.get("slug") == slug:
                MessageBox(i18n.t("provider_err"), i18n.t("provider_err_exist_global", slug=slug), self.window()).exec()
                return
                
        new_provider = {
            "slug": slug,
            "label": label if label else slug.upper(),
            "base_url": base_url,
            "model": model,
            "wire_api": wire_api
        }
        
        file_providers.append(new_provider)
        
        try:
            with open(self.providers_path, 'w', encoding='utf-8') as f:
                json.dump(file_providers, f, indent=4, ensure_ascii=False)
            
            # 清空表单
            self.slugInput.clear()
            self.labelInput.clear()
            self.baseUrlInput.clear()
            self.modelInput.clear()
            
            self.load_providers()
            MessageBox(i18n.t("provider_success"), i18n.t("provider_save_success"), self.window()).exec()
        except Exception as e:
            MessageBox(i18n.t("provider_save_fail"), str(e), self.window()).exec()

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if item is None:
            return
            
        row = item.row()
        is_db = self.table.item(row, 0).text().startswith(i18n.t("provider_src_user", id="").split(":")[0])
        slug = self.table.item(row, 1).text()

        from qfluentwidgets import RoundMenu, Action
        menu = RoundMenu(parent=self)
        
        delete_action = Action(FluentIcon.DELETE, i18n.t("provider_ctx_del"), triggered=lambda: self.delete_provider(slug, is_db))
        menu.addAction(delete_action)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def delete_provider(self, slug, is_db):
        if is_db:
            dialog = MessageBox(i18n.t("user_del_confirm_title"), i18n.t("provider_del_db_confirm", slug=slug), self.window())
            if dialog.exec():
                try:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM provider_configs WHERE slug = ?", (slug,))
                    conn.commit()
                    conn.close()
                    self.load_providers()
                    MessageBox(i18n.t("provider_success"), i18n.t("provider_del_db_success"), self.window()).exec()
                except Exception as e:
                    MessageBox(i18n.t("provider_del_fail"), str(e), self.window()).exec()
        else:
            dialog = MessageBox(i18n.t("user_del_confirm_title"), i18n.t("provider_del_global_confirm", slug=slug), self.window())
            if dialog.exec():
                file_providers = [p for p in self.providers if not p.get("is_db", False) and p.get("slug") != slug]
                try:
                    with open(self.providers_path, 'w', encoding='utf-8') as f:
                        json.dump(file_providers, f, indent=4, ensure_ascii=False)
                    self.load_providers()
                    MessageBox(i18n.t("provider_success"), i18n.t("provider_del_global_success"), self.window()).exec()
                except Exception as e:
                    MessageBox(i18n.t("provider_del_fail"), str(e), self.window()).exec()


class SettingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(40, 50, 40, 40)
        self.vBoxLayout.setSpacing(20)

        # 标题
        self.titleLabel = SubtitleLabel(i18n.t("setting_title"), self)
        self.vBoxLayout.addWidget(self.titleLabel)

        # 端口设置卡片
        self.portCard = CardWidget(self)
        self.portLayout = QHBoxLayout(self.portCard)
        self.portLayout.setContentsMargins(20, 20, 20, 20)
        
        self.portInfo = QVBoxLayout()
        self.portTitle = BodyLabel(i18n.t("setting_port_title"), self)
        self.portDesc = BodyLabel(i18n.t("setting_port_desc"), self)
        self.portDesc.setTextColor(QColor(128, 128, 128), QColor(128, 128, 128))
        self.portInfo.addWidget(self.portTitle)
        self.portInfo.addWidget(self.portDesc)
        
        self.portSpinBox = SpinBox(self)
        self.portSpinBox.setRange(1024, 65535)
        self.portSpinBox.setFixedWidth(200)  # Increased width for better visibility
        
        # 语言设置卡片
        self.langCard = CardWidget(self)
        self.langLayout = QHBoxLayout(self.langCard)
        self.langLayout.setContentsMargins(20, 20, 20, 20)
        
        self.langInfo = QVBoxLayout()
        self.langTitle = BodyLabel(i18n.t("setting_lang_title"), self)
        self.langDesc = BodyLabel(i18n.t("setting_lang_desc"), self)
        self.langDesc.setTextColor(QColor(128, 128, 128), QColor(128, 128, 128))
        self.langInfo.addWidget(self.langTitle)
        self.langInfo.addWidget(self.langDesc)
        
        self.langCombo = ComboBox(self)
        self.langCombo.addItem("中文 (简体)", userData="zh_CN")
        self.langCombo.addItem("English", userData="en_US")
        self.langCombo.setFixedWidth(200)
        
        # Load saved config
        self.config_path = os.path.join("local_web_portal", "launcher_config.json")
        self.load_config()
        
        self.saveBtn = PrimaryPushButton(i18n.t("setting_save"), self)
        self.saveBtn.clicked.connect(self.save_config)
        
        self.portLayout.addLayout(self.portInfo)
        self.portLayout.addStretch(1)
        self.portLayout.addWidget(self.portSpinBox)
        
        self.langLayout.addLayout(self.langInfo)
        self.langLayout.addStretch(1)
        self.langLayout.addWidget(self.langCombo)
        
        self.vBoxLayout.addWidget(self.portCard)
        self.vBoxLayout.addWidget(self.langCard)
        
        # 保存按钮单独放一行
        self.btnLayout = QHBoxLayout()
        self.btnLayout.addStretch(1)
        self.btnLayout.addWidget(self.saveBtn)
        self.vBoxLayout.addLayout(self.btnLayout)
        
        self.vBoxLayout.addStretch(1)

    def load_config(self):
        default_port = 8010
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    port = config.get("port", default_port)
                    self.portSpinBox.setValue(port)
                    
                    lang = config.get("lang", "zh_CN")
                    if lang == "en_US":
                        self.langCombo.setCurrentIndex(1)
                    else:
                        self.langCombo.setCurrentIndex(0)
                    return
            except Exception:
                pass
        self.portSpinBox.setValue(default_port)
        self.langCombo.setCurrentIndex(0)

    def save_config(self):
        port = self.portSpinBox.value()
        lang = self.langCombo.currentData()
        
        config = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except:
                pass
                
        config["port"] = port
        config["lang"] = lang
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            i18n.set_lang(lang) # 更新内存中的语言设置
            MessageBox(i18n.t("setting_save_success"), i18n.t("setting_save_msg"), self.window()).exec()
        except Exception as e:
            MessageBox(i18n.t("setting_save_fail"), str(e), self.window()).exec()

class UserManagementWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(40, 50, 40, 40)
        self.vBoxLayout.setSpacing(20)

        # 标题和刷新按钮区
        self.headerLayout = QHBoxLayout()
        self.titleLabel = SubtitleLabel(i18n.t("user_title"), self)
        self.refreshBtn = PushButton(FluentIcon.SYNC, i18n.t("user_refresh"), self)
        self.refreshBtn.clicked.connect(self.load_users)
        
        self.headerLayout.addWidget(self.titleLabel)
        self.headerLayout.addStretch(1)
        self.headerLayout.addWidget(self.refreshBtn)
        self.vBoxLayout.addLayout(self.headerLayout)

        # 提示信息
        self.infoLabel = BodyLabel(i18n.t("user_desc"), self)
        self.infoLabel.setTextColor(QColor(128, 128, 128), QColor(128, 128, 128))
        self.vBoxLayout.addWidget(self.infoLabel)

        # 表格卡片
        self.tableCard = CardWidget(self)
        self.tableLayout = QVBoxLayout(self.tableCard)
        self.tableLayout.setContentsMargins(10, 10, 10, 10)
        
        self.table = TableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([i18n.t("user_table_id"), i18n.t("user_table_email"), i18n.t("user_table_time")])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(TableWidget.NoEditTriggers)
        # 使列宽自适应
        self.table.horizontalHeader().setStretchLastSection(True)
        self.tableLayout.addWidget(self.table)
        
        self.vBoxLayout.addWidget(self.tableCard, 1) # 1 means stretch

        # 右键菜单
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        self.db_path = os.path.join("local_web_portal", "data", "app.db")
        self.load_users()

    def get_db_connection(self):
        if not os.path.exists(self.db_path):
            return None
        try:
            return sqlite3.connect(self.db_path)
        except:
            return None

    def load_users(self):
        self.table.setRowCount(0)
        conn = self.get_db_connection()
        if not conn:
            self.infoLabel.setText(i18n.t("user_no_db"))
            return
            
        try:
            cursor = conn.cursor()
            # 查询 users 表：使用实际的列 email 和 created_at
            cursor.execute("SELECT id, email, created_at FROM users")
            users = cursor.fetchall()
            
            self.table.setRowCount(len(users))
            from PySide6.QtWidgets import QTableWidgetItem
            
            for row_idx, user in enumerate(users):
                self.table.setItem(row_idx, 0, QTableWidgetItem(str(user[0])))
                self.table.setItem(row_idx, 1, QTableWidgetItem(str(user[1])))
                self.table.setItem(row_idx, 2, QTableWidgetItem(str(user[2])))
                
            self.infoLabel.setText(i18n.t("user_count", count=len(users)))
        except sqlite3.OperationalError:
            self.infoLabel.setText(i18n.t("user_no_table"))
        finally:
            conn.close()

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if item is None:
            return
            
        row = item.row()
        user_id = self.table.item(row, 0).text()
        username = self.table.item(row, 1).text()

        from qfluentwidgets import RoundMenu, Action
        menu = RoundMenu(parent=self)
        
        # 修正：qfluentwidgets 的 Action 创建方式不同于原生的 QAction
        delete_action = Action(FluentIcon.DELETE, i18n.t("user_ctx_del"), triggered=lambda: self.delete_user(user_id, username))
        menu.addAction(delete_action)
        
        # 将局部坐标转换为全局坐标
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def delete_user(self, user_id, username):
        dialog = MessageBox(i18n.t("user_del_confirm_title"), i18n.t("user_del_confirm_msg", username=username), self.window())
        if dialog.exec():
            conn = self.get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                    conn.commit()
                    self.load_users()
                    MessageBox(i18n.t("provider_success"), i18n.t("user_del_success", username=username), self.window()).exec()
                except Exception as e:
                    MessageBox(i18n.t("provider_err"), f"{i18n.t('provider_del_fail')}: {str(e)}", self.window()).exec()
                finally:
                    conn.close()


class DatabaseWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(40, 50, 40, 40)
        self.vBoxLayout.setSpacing(20)

        # 标题
        self.titleLabel = SubtitleLabel(i18n.t("db_title"), self)
        self.vBoxLayout.addWidget(self.titleLabel)

        # 1. 网页端数据库管理
        self.webDbCard = CardWidget(self)
        self.webDbLayout = QHBoxLayout(self.webDbCard)
        self.webDbLayout.setContentsMargins(20, 20, 20, 20)
        
        self.webDbInfo = QVBoxLayout()
        self.webDbTitle = BodyLabel(i18n.t("db_web_title"), self)
        self.webDbDesc = BodyLabel(i18n.t("db_web_desc"), self)
        self.webDbDesc.setTextColor(QColor(128, 128, 128), QColor(128, 128, 128))
        self.webDbInfo.addWidget(self.webDbTitle)
        self.webDbInfo.addWidget(self.webDbDesc)
        
        self.webDbBtn = PushButton(i18n.t("db_clear_btn"), self)
        self.webDbBtn.clicked.connect(self.clear_web_db)
        
        self.webDbLayout.addLayout(self.webDbInfo)
        self.webDbLayout.addStretch(1)
        self.webDbLayout.addWidget(self.webDbBtn)
        self.vBoxLayout.addWidget(self.webDbCard)

        # 2. 向量数据库管理
        self.vectorDbCard = CardWidget(self)
        self.vectorDbLayout = QHBoxLayout(self.vectorDbCard)
        self.vectorDbLayout.setContentsMargins(20, 20, 20, 20)
        
        self.vectorDbInfo = QVBoxLayout()
        self.vectorDbTitle = BodyLabel(i18n.t("db_vector_title"), self)
        self.vectorDbDesc = BodyLabel(i18n.t("db_vector_desc"), self)
        self.vectorDbDesc.setTextColor(QColor(128, 128, 128), QColor(128, 128, 128))
        self.vectorDbInfo.addWidget(self.vectorDbTitle)
        self.vectorDbInfo.addWidget(self.vectorDbDesc)
        
        self.vectorDbBtn = PushButton(i18n.t("db_clear_btn"), self)
        self.vectorDbBtn.clicked.connect(self.clear_vector_db)
        
        self.vectorDbLayout.addLayout(self.vectorDbInfo)
        self.vectorDbLayout.addStretch(1)
        self.vectorDbLayout.addWidget(self.vectorDbBtn)
        self.vBoxLayout.addWidget(self.vectorDbCard)

        # 3. 运行日志管理
        self.runsCard = CardWidget(self)
        self.runsLayout = QHBoxLayout(self.runsCard)
        self.runsLayout.setContentsMargins(20, 20, 20, 20)
        
        self.runsInfo = QVBoxLayout()
        self.runsTitle = BodyLabel(i18n.t("db_runs_title"), self)
        self.runsDesc = BodyLabel(i18n.t("db_runs_desc"), self)
        self.runsDesc.setTextColor(QColor(128, 128, 128), QColor(128, 128, 128))
        self.runsInfo.addWidget(self.runsTitle)
        self.runsInfo.addWidget(self.runsDesc)
        
        self.runsBtn = PushButton(i18n.t("db_clear_btn"), self)
        self.runsBtn.clicked.connect(self.clear_runs)
        
        self.runsLayout.addLayout(self.runsInfo)
        self.runsLayout.addStretch(1)
        self.runsLayout.addWidget(self.runsBtn)
        self.vBoxLayout.addWidget(self.runsCard)

        self.vBoxLayout.addStretch(1)

    def _delete_target(self, title, content, target_path, is_file=False):
        dialog = MessageBox(title, content, self.window())
        if dialog.exec():
            try:
                import shutil
                if os.path.exists(target_path):
                    if is_file:
                        os.remove(target_path)
                    else:
                        for item in os.listdir(target_path):
                            item_path = os.path.join(target_path, item)
                            if item == ".keep":
                                continue
                            if os.path.isfile(item_path):
                                os.remove(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                    
                    MessageBox(i18n.t("db_clear_success"), i18n.t("db_clear_success_msg", target=target_path), self.window()).exec()
                else:
                    MessageBox(i18n.t("db_clear_none"), i18n.t("db_clear_none_msg"), self.window()).exec()
            except Exception as e:
                MessageBox(i18n.t("db_clear_fail"), f"{i18n.t('provider_err')}：\n{str(e)}", self.window()).exec()

    def clear_web_db(self):
        db_path = os.path.join("local_web_portal", "data", "app.db")
        self._delete_target(i18n.t("db_confirm_title"), i18n.t("db_web_confirm"), db_path, is_file=True)

    def clear_vector_db(self):
        self._delete_target(i18n.t("db_confirm_title"), i18n.t("db_vector_confirm"), "vector_db")

    def clear_runs(self):
        self._delete_target(i18n.t("db_confirm_title"), i18n.t("db_runs_confirm"), "runs")

class InitProcessThread(QThread):
    log_signal = Signal(str)
    step1_signal = Signal(str)
    step2_signal = Signal(str)
    step3_signal = Signal(str)
    finished_signal = Signal(bool)

    def run(self):
        try:
            # ---------------------------------------------------------
            # 步骤 1: 创建.env环境
            # ---------------------------------------------------------
            self.step1_signal.emit(i18n.t("init_doing"))
            self.log_signal.emit("=> [步骤 1] 正在创建 .env 虚拟环境...")
            
            env_dir = ".env"
            if not os.path.exists(env_dir):
                import shutil
                system_python = shutil.which("python") or shutil.which("python3") or "python"
                result = subprocess.run([system_python, "-m", "venv", env_dir], capture_output=True, text=True)
                if result.returncode != 0:
                    self.log_signal.emit("❌ 错误: 创建虚拟环境失败\n" + result.stderr)
                    self.step1_signal.emit(i18n.t("init_fail"))
                    self.finished_signal.emit(False)
                    return
                self.log_signal.emit("✅ 虚拟环境创建成功。")
            else:
                self.log_signal.emit("✅ 虚拟环境 '.env' 已存在，跳过创建。")
            self.step1_signal.emit(i18n.t("init_done"))
            
            # ---------------------------------------------------------
            # 步骤 2: 进入env环境 (设置执行路径)
            # ---------------------------------------------------------
            self.step2_signal.emit(i18n.t("init_doing"))
            self.log_signal.emit("\n=> [步骤 2] 进入 env 环境并配置路径...")
            if os.name == 'nt':
                python_exe = os.path.join(env_dir, "Scripts", "python.exe")
            else:
                python_exe = os.path.join(env_dir, "bin", "python")
                
            if not os.path.exists(python_exe):
                self.log_signal.emit("❌ 错误: 找不到虚拟环境中的 Python 解释器。")
                self.step2_signal.emit(i18n.t("init_fail"))
                self.finished_signal.emit(False)
                return
                
            self.log_signal.emit(f"✅ 已锁定虚拟环境 Python 路径:\n   {os.path.abspath(python_exe)}")
            self.step2_signal.emit(i18n.t("init_done"))
            
            # ---------------------------------------------------------
            # 步骤 3: 安装扩展
            # ---------------------------------------------------------
            self.step3_signal.emit(i18n.t("init_doing"))
            self.log_signal.emit("\n=> [步骤 3] 开始安装扩展...")
            
            req_files = ["requirements.txt", os.path.join("local_web_portal", "requirements.txt")]
            for req in req_files:
                if not os.path.exists(req):
                    self.log_signal.emit(f"❌ 错误: 找不到 {req} 文件。")
                    self.step3_signal.emit(i18n.t("init_fail"))
                    self.finished_signal.emit(False)
                    return
                
            self.log_signal.emit("正在使用 pip 安装依赖，请耐心等待...")
            
            # 使用 Popen 以便实时获取输出
            process = subprocess.Popen(
                [python_exe, "-m", "pip", "install", "-r", req_files[0], "-r", req_files[1], "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            for line in iter(process.stdout.readline, ''):
                line_str = line.strip()
                if line_str:
                    self.log_signal.emit(line_str)
                
            process.wait()
            
            if process.returncode == 0:
                self.log_signal.emit("\n✅ 所有扩展安装完成！")
                self.step3_signal.emit(i18n.t("init_done"))
                self.log_signal.emit("=========================================")
                self.log_signal.emit("🎉 初始化全部成功，请选择启动模式！")
                self.log_signal.emit("=========================================")
                self.finished_signal.emit(True)
            else:
                self.log_signal.emit(f"\n❌ 扩展安装失败，退出码: {process.returncode}")
                self.step3_signal.emit(i18n.t("init_fail"))
                self.finished_signal.emit(False)
                
        except Exception as e:
            self.log_signal.emit(f"\n❌ 发生异常: {str(e)}")
            self.finished_signal.emit(False)


class ProcessReaderThread(QThread):
    log_signal = Signal(str)

    def __init__(self, process):
        super().__init__()
        self.process = process

    def run(self):
        try:
            # 以字节流形式读取，并使用 utf-8 解码，忽略无法解码的字符以防止崩溃
            for line in iter(self.process.stdout.readline, b''):
                if line:
                    decoded_line = line.decode('utf-8', errors='replace')
                    self.log_signal.emit(decoded_line)
            self.process.stdout.close()
        except Exception:
            pass


class InitWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(40, 50, 40, 40)  # Top margin increased for title bar space
        self.vBoxLayout.setSpacing(20)

        # 标题
        self.titleLabel = SubtitleLabel(i18n.t("init_title"), self)
        self.vBoxLayout.addWidget(self.titleLabel, 0, Qt.AlignHCenter)

        # 步骤卡片
        self.stepCard = CardWidget(self)
        self.stepLayout = QVBoxLayout(self.stepCard)
        self.stepLayout.setContentsMargins(20, 20, 20, 20)
        self.stepLayout.setSpacing(15)

        self.step1_layout = QHBoxLayout()
        self.step1_label = BodyLabel(i18n.t("init_step1"), self)
        self.step1_status = BodyLabel(i18n.t("init_wait"), self)
        self.step1_status.setTextColor(QColor(128, 128, 128), QColor(128, 128, 128))
        self.step1_layout.addWidget(self.step1_label)
        self.step1_layout.addStretch(1)
        self.step1_layout.addWidget(self.step1_status)

        self.step2_layout = QHBoxLayout()
        self.step2_label = BodyLabel(i18n.t("init_step2"), self)
        self.step2_status = BodyLabel(i18n.t("init_wait"), self)
        self.step2_status.setTextColor(QColor(128, 128, 128), QColor(128, 128, 128))
        self.step2_layout.addWidget(self.step2_label)
        self.step2_layout.addStretch(1)
        self.step2_layout.addWidget(self.step2_status)

        self.step3_layout = QHBoxLayout()
        self.step3_label = BodyLabel(i18n.t("init_step3"), self)
        self.step3_status = BodyLabel(i18n.t("init_wait"), self)
        self.step3_status.setTextColor(QColor(128, 128, 128), QColor(128, 128, 128))
        self.step3_layout.addWidget(self.step3_label)
        self.step3_layout.addStretch(1)
        self.step3_layout.addWidget(self.step3_status)

        self.stepLayout.addLayout(self.step1_layout)
        self.stepLayout.addLayout(self.step2_layout)
        self.stepLayout.addLayout(self.step3_layout)
        
        self.vBoxLayout.addWidget(self.stepCard)

        # 日志区
        self.logText = TextEdit(self)
        self.logText.setReadOnly(True)
        self.logText.setFont(QFont("Consolas", 10))
        self.vBoxLayout.addWidget(self.logText, 1)

        # 按钮区
        self.btnLayout = QHBoxLayout()
        self.startBtn = PrimaryPushButton(i18n.t("init_start_btn"), self)
        self.startBtn.clicked.connect(self.start_init)
        
        self.btnLayout.addStretch(1)
        self.btnLayout.addWidget(self.startBtn)
        self.btnLayout.addStretch(1)
        
        self.vBoxLayout.addLayout(self.btnLayout)

    def log(self, text):
        self.logText.append(text)

    def start_init(self):
        self.startBtn.setEnabled(False)
        self.log(i18n.t("init_log_start"))
        
        self.init_thread = InitProcessThread()
        self.init_thread.log_signal.connect(self.log)
        self.init_thread.step1_signal.connect(self.update_step1)
        self.init_thread.step2_signal.connect(self.update_step2)
        self.init_thread.step3_signal.connect(self.update_step3)
        self.init_thread.finished_signal.connect(self.on_init_finished)
        self.init_thread.start()

    def update_step1(self, status):
        self.step1_status.setText(status)
        if i18n.t("init_doing") in status:
            self.step1_status.setTextColor(QColor(0, 120, 212), QColor(0, 120, 212))
        elif i18n.t("init_fail") in status:
            self.step1_status.setTextColor(QColor(255, 0, 0), QColor(255, 0, 0))
        else:
            self.step1_status.setTextColor(QColor(16, 124, 16), QColor(16, 124, 16))

    def update_step2(self, status):
        self.step2_status.setText(status)
        if i18n.t("init_doing") in status:
            self.step2_status.setTextColor(QColor(0, 120, 212), QColor(0, 120, 212))
        elif i18n.t("init_fail") in status:
            self.step2_status.setTextColor(QColor(255, 0, 0), QColor(255, 0, 0))
        else:
            self.step2_status.setTextColor(QColor(16, 124, 16), QColor(16, 124, 16))

    def update_step3(self, status):
        self.step3_status.setText(status)
        if i18n.t("init_doing") in status:
            self.step3_status.setTextColor(QColor(0, 120, 212), QColor(0, 120, 212))
        elif i18n.t("init_fail") in status:
            self.step3_status.setTextColor(QColor(255, 0, 0), QColor(255, 0, 0))
        else:
            self.step3_status.setTextColor(QColor(16, 124, 16), QColor(16, 124, 16))

    def on_init_finished(self, success):
        if not success:
            self.startBtn.setEnabled(True)
        else:
            # 成功后，通知主窗口切换界面
            self.window().show_main_interface()


class MainWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        
        self.current_process = None
        self.reader_thread = None

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(40, 50, 40, 40)  # Top margin increased for title bar space
        self.vBoxLayout.setSpacing(20)

        # 顶部控制区
        self.topFrame = CardWidget(self)
        self.topLayout = QHBoxLayout(self.topFrame)
        self.topLayout.setContentsMargins(20, 15, 20, 15)

        self.titleLabel = SubtitleLabel(i18n.t("main_title"), self)
        self.topLayout.addWidget(self.titleLabel)
        self.topLayout.addStretch(1)

        self.runWebBtn = PrimaryPushButton(i18n.t("main_start_btn"), self)
        self.runWebBtn.clicked.connect(self.run_web)
        
        self.openWebBtn = PushButton(i18n.t("main_open_btn"), self)
        self.openWebBtn.clicked.connect(self.open_browser)
        self.openWebBtn.setEnabled(False)
        
        self.stopBtn = PushButton(i18n.t("main_stop_btn"), self)
        self.stopBtn.clicked.connect(self.stop_process)
        self.stopBtn.setEnabled(False)

        self.topLayout.addWidget(self.runWebBtn)
        self.topLayout.addWidget(self.openWebBtn)
        self.topLayout.addWidget(self.stopBtn)

        self.vBoxLayout.addWidget(self.topFrame)

        # 虚拟终端输出区
        self.termLabel = BodyLabel(i18n.t("main_term_title"), self)
        self.vBoxLayout.addWidget(self.termLabel)

        self.termText = QTextEdit(self)
        self.termText.setReadOnly(True)
        self.termText.setFont(QFont("Consolas", 10))
        # 类似终端的黑底白字
        self.termText.setStyleSheet("QTextEdit { background-color: #1e1e1e; color: #d4d4d4; }")
        self.vBoxLayout.addWidget(self.termText, 1)

        self.term_out(i18n.t("main_welcome"))

    def term_out(self, text):
        from PySide6.QtGui import QTextCursor
        self.termText.moveCursor(QTextCursor.MoveOperation.End)
        self.termText.insertPlainText(text)
        self.termText.moveCursor(QTextCursor.MoveOperation.End)

    def open_browser(self):
        import webbrowser
        port = getattr(self, 'current_port', "8010")
        webbrowser.open(f"http://127.0.0.1:{port}")

    def stop_process(self):
        if self.current_process and self.current_process.poll() is None:
            self.term_out(i18n.t("main_stopping"))
            try:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.current_process.pid)], capture_output=True)
                else:
                    self.current_process.terminate()
            except Exception as e:
                self.term_out(i18n.t("main_stop_err", err=str(e)))
            
            self.current_process = None
            self.term_out(i18n.t("main_stopped"))
            
        self.runWebBtn.setEnabled(True)
        self.openWebBtn.setEnabled(False)
        self.stopBtn.setEnabled(False)

    def get_python_exe(self):
        env_dir = ".env"
        if os.name == 'nt':
            return os.path.join(env_dir, "Scripts", "python.exe")
        else:
            return os.path.join(env_dir, "bin", "python")

    def run_web(self):
        # Load port from config if exists
        port = "8010"
        config_path = os.path.join("local_web_portal", "launcher_config.json")
        if os.path.exists(config_path):
            try:
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    port = str(config.get("port", 8010))
            except:
                pass
                
        self.term_out(i18n.t("main_starting", port=port))
        self.runWebBtn.setEnabled(False)
        self.openWebBtn.setEnabled(True)
        self.stopBtn.setEnabled(True)
        self.current_port = port
        
        python_exe = self.get_python_exe()
        
        env = os.environ.copy()
        env["EMBEDDING_MODEL"] = "none"
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        
        # 注入自定义 Provider 环境变量
        providers_path = os.path.join("local_web_portal", "custom_providers.json")
        if os.path.exists(providers_path):
            try:
                with open(providers_path, 'r', encoding='utf-8') as f:
                    # 直接把整个 JSON 内容传给后端
                    env["WEB_EXTRA_PROVIDERS_JSON"] = f.read()
            except:
                pass
        
        try:
            self.current_process = subprocess.Popen(
                [python_exe, "-u", "-m", "uvicorn", "local_web_portal.app.main:app", "--host", "127.0.0.1", "--port", port],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                # 不再使用 text=True，由 ProcessReaderThread 负责处理字节流和 UTF-8 解码
                bufsize=0,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            self.term_out(i18n.t("main_visit", port=port))
            
            # 记录当前使用的端口以便 open_browser 使用
            self.current_port = port
            
            self.reader_thread = ProcessReaderThread(self.current_process)
            self.reader_thread.log_signal.connect(self.term_out)
            self.reader_thread.start()
        except Exception as e:
            self.term_out(i18n.t("main_start_err", err=str(e)))
            self.stop_process()


class AppWindow(MSFluentWindow):
    def __init__(self):
        super().__init__()
        
        # Determine base path for resources (handles PyInstaller bundle)
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        icon_path = os.path.join(base_path, 'colong.png')
        
        # Window configuration
        self.setWindowTitle(i18n.t("window_title"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(800, 600)
        self.setMinimumSize(600, 500)  # Allow resizing but prevent it from getting too small
        
        # Center the window
        desktop = QApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        # Set theme
        setTheme(Theme.AUTO)

        # Initialize widgets
        self.init_widget = InitWidget(self)
        self.init_widget.setObjectName("initInterface")
        self.main_widget = MainWidget(self)
        self.main_widget.setObjectName("mainInterface")
        self.user_widget = UserManagementWidget(self)
        self.user_widget.setObjectName("userInterface")
        self.provider_widget = ProviderManagementWidget(self)
        self.provider_widget.setObjectName("providerInterface")
        self.db_widget = DatabaseWidget(self)
        self.db_widget.setObjectName("dbInterface")
        self.setting_widget = SettingWidget(self)
        self.setting_widget.setObjectName("settingInterface")
        
        # We only hide navigation bar when in init screen, and show it later
        
        # Add main, user, provider and db widgets to the sidebar first
        self.addSubInterface(self.main_widget, FluentIcon.PLAY, i18n.t("nav_launch"))
        self.addSubInterface(self.user_widget, FluentIcon.PEOPLE, i18n.t("nav_user"))
        self.addSubInterface(self.provider_widget, FluentIcon.GLOBE, i18n.t("nav_provider"))
        self.addSubInterface(self.db_widget, FluentIcon.FOLDER, i18n.t("nav_db"))
        
        # Add setting widget to the bottom of the sidebar
        self.addSubInterface(self.setting_widget, FluentIcon.SETTING, i18n.t("nav_settings"), position=NavigationItemPosition.BOTTOM)
        
        # Check if already initialized
        if self.check_is_initialized():
            self.show_main_interface()
        else:
            # Add init widget to stack but NOT to the sidebar navigation
            self.stackedWidget.addWidget(self.init_widget)
            self.navigationInterface.hide()
            self.switchTo(self.init_widget)

    def check_is_initialized(self):
        """Check if the environment is already initialized"""
        env_dir = ".env"
        if os.name == 'nt':
            python_exe = os.path.join(env_dir, "Scripts", "python.exe")
        else:
            python_exe = os.path.join(env_dir, "bin", "python")
            
        # Check if python executable exists in the virtual environment
        if not os.path.exists(python_exe):
            return False
            
        # We assume that if the environment exists and uvicorn is installed, it's fully initialized
        try:
            result = subprocess.run(
                [python_exe, "-c", "import uvicorn; import fastapi"], 
                capture_output=True, 
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.returncode == 0
        except Exception:
            return False

    def show_main_interface(self):
        self.navigationInterface.show()
        self.switchTo(self.main_widget)

    def closeEvent(self, event):
        # 检查是否还有后台进程在运行
        if hasattr(self, 'main_widget') and self.main_widget.current_process is not None:
            if self.main_widget.current_process.poll() is None:
                dialog = MessageBox(
                    i18n.t("exit_confirm_title"),
                    i18n.t("exit_confirm_msg"),
                    self
                )
                if dialog.exec():
                    self.main_widget.stop_process()
                    event.accept()
                else:
                    event.ignore()
                    return
        event.accept()


if __name__ == '__main__':
    # Enable High DPI support (PySide6 / Qt6 no longer requires these attributes)
    app = QApplication(sys.argv)
    window = AppWindow()
    window.show()
    sys.exit(app.exec())