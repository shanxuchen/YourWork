/**
 * YourWork - 应用入口
 * 全局初始化和通用功能
 */

(function() {
    'use strict';

    /**
     * 应用配置
     */
    const config = {
        api_base: '/api/v1',
        toast_duration: 3000,
        auto_refresh_interval: 60000  // 1分钟
    };

    /**
     * 应用状态
     */
    const state = {
        current_user: null,
        is_initialized: false
    };

    /**
     * 初始化应用
     */
    async function init_app() {
        if (state.is_initialized) {
            return;
        }

        console.log('[App] 开始初始化应用');

        // 初始化认证模块
        const user = await AuthModule.init();
        state.current_user = user;

        // 设置全局事件监听
        setup_global_events();

        state.is_initialized = true;
        console.log('[App] 应用初始化完成');
    }

    /**
     * 设置全局事件监听
     */
    function setup_global_events() {
        // 监听所有表单提交
        document.addEventListener('submit', handle_form_submit);

        // 监听所有按钮点击
        document.addEventListener('click', handle_button_click);

        // 定时刷新未读消息数
        setInterval(function() {
            if (state.current_user) {
                MessageModule.refresh_unread_count();
            }
        }, config.auto_refresh_interval);
    }

    /**
     * 处理表单提交
     */
    async function handle_form_submit(e) {
        const form = e.target;
        if (!form.classList.contains('api-form')) {
            return;
        }

        e.preventDefault();

        const action = form.getAttribute('data-action');
        const method = form.getAttribute('data-method') || 'POST';
        const success_redirect = form.getAttribute('data-redirect');
        const success_message = form.getAttribute('data-success');

        // 收集表单数据
        const form_data = new FormData(form);
        const data = {};
        form_data.forEach(function(value, key) {
            data[key] = value;
        });

        // 处理文件上传
        const has_files = form.querySelector('input[type="file"]');
        if (has_files) {
            await handle_file_upload(action, form_data, success_redirect, success_message);
            return;
        }

        // 发送请求
        try {
            let result;
            switch (method.toUpperCase()) {
                case 'POST':
                    result = await api_post(action, data);
                    break;
                case 'PUT':
                    result = await api_put(action, data);
                    break;
                default:
                    result = await api_post(action, data);
            }

            if (result.code === 0) {
                if (success_message) {
                    YWUtils.show_toast(success_message, 'success');
                }
                if (success_redirect) {
                    window.location.href = success_redirect;
                }
            } else {
                YWUtils.show_toast(result.message || '操作失败', 'error');
            }
        } catch (e) {
            console.log('[App] 表单提交失败:', e);
            YWUtils.show_toast('网络错误，请重试', 'error');
        }
    }

    /**
     * 处理文件上传
     */
    async function handle_file_upload(action, form_data, success_redirect, success_message) {
        try {
            const result = await api_upload(action, form_data);

            if (result.code === 0) {
                if (success_message) {
                    YWUtils.show_toast(success_message, 'success');
                }
                if (success_redirect) {
                    window.location.href = success_redirect;
                }
            } else {
                YWUtils.show_toast(result.message || '上传失败', 'error');
            }
        } catch (e) {
            console.log('[App] 文件上传失败:', e);
            YWUtils.show_toast('上传失败，请重试', 'error');
        }
    }

    /**
     * 处理按钮点击
     */
    function handle_button_click(e) {
        const btn = e.target.closest('.api-btn');
        if (!btn) return;

        e.preventDefault();

        const action = btn.getAttribute('data-action');
        const method = btn.getAttribute('data-method') || 'POST';
        const confirm_msg = btn.getAttribute('data-confirm');
        const success_message = btn.getAttribute('data-success');

        // 确认对话框
        if (confirm_msg && !confirm(confirm_msg)) {
            return;
        }

        // 发送请求
        (async function() {
            try {
                let result;
                switch (method.toUpperCase()) {
                    case 'DELETE':
                        result = await api_delete(action);
                        break;
                    case 'PUT':
                        result = await api_put(action);
                        break;
                    default:
                        result = await api_post(action);
                }

                if (result.code === 0) {
                    if (success_message) {
                        YWUtils.show_toast(success_message, 'success');
                    }
                    // 刷新页面
                    if (btn.classList.contains('refresh-on-success')) {
                        window.location.reload();
                    }
                } else {
                    YWUtils.show_toast(result.message || '操作失败', 'error');
                }
            } catch (e) {
                console.log('[App] 按钮操作失败:', e);
                YWUtils.show_toast('操作失败，请重试', 'error');
            }
        })();
    }

    /**
     * 渲染用户信息
     */
    function render_user_info() {
        const user = state.current_user;
        if (!user) return;

        // 更新用户显示名称
        const user_info_el = document.getElementById('user-info');
        if (user_info_el) {
            user_info_el.textContent = AuthModule.get_display_name();
        }

        // 显示/隐藏管理员链接
        if (AuthModule.is_admin()) {
            const admin_links = document.querySelectorAll('.admin-only');
            admin_links.forEach(function(el) {
                el.style.display = '';
            });
        }
    }

    /**
     * 格式化日期（全局方法，兼容旧代码）
     */
    function format_date(date_str) {
        return YWUtils.format_date(date_str);
    }

    /**
     * 格式化文件大小（全局方法，兼容旧代码）
     */
    function format_file_size(bytes) {
        return YWUtils.format_file_size(bytes);
    }

    /**
     * HTML 转义（全局方法，兼容旧代码）
     */
    function escape_html(text) {
        return YWUtils.escape_html(text);
    }

    /**
     * 显示 Toast（全局方法，兼容旧代码）
     */
    function show_toast(message, type) {
        YWUtils.show_toast(message, type);
    }

    /**
     * 退出登录（全局方法）
     */
    async function logout() {
        await AuthModule.logout();
    }

    // 导出到全局
    window.YWApp = {
        config: config,
        state: state,
        init: init_app,
        render_user_info: render_user_info,
        format_date: format_date,
        format_file_size: format_file_size,
        escape_html: escape_html,
        show_toast: show_toast,
        logout: logout
    };

    // 全局方法（兼容旧代码）
    window.format_date = format_date;
    window.format_file_size = format_file_size;
    window.escape_html = escape_html;
    window.show_toast = show_toast;
    window.logout = logout;

    // 页面加载完成后自动初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            init_app();
        });
    } else {
        init_app();
    }

    console.log('[INFO] app.js 加载完成');
})();
