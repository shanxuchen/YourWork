/**
 * YourWork - 工具函数库
 * 通用工具函数和辅助方法
 */

(function() {
    'use strict';

    // ==================== 日志函数 ====================
    const LOG_PREFIX = '[YourWork]';

    /**
     * 格式化时间
     */
    function format_time(date) {
        if (!date) return '';
        const d = new Date(date);
        const hours = String(d.getHours()).padStart(2, '0');
        const minutes = String(d.getMinutes()).padStart(2, '0');
        const seconds = String(d.getSeconds()).padStart(2, '0');
        return `${hours}:${minutes}:${seconds}`;
    }

    /**
     * 日志输出 - 与后端日志格式一致
     */
    function log(level, module, message, data) {
        const time = format_time(new Date());
        const prefix = `${LOG_PREFIX}[${level}] ${time} | ${module} |`;

        if (data !== undefined) {
            console.log(prefix, message, data);
        } else {
            console.log(prefix, message);
        }
    }

    // 导出日志函数
    window.logger = {
        debug: function(module, message, data) { log('DEBUG', module, message, data); },
        info: function(module, message, data) { log('INFO', module, message, data); },
        warning: function(module, message, data) { log('WARNING', module, message, data); },
        error: function(module, message, data) { log('ERROR', module, message, data); }
    };

    // ==================== 工具函数 ====================

    /**
     * 格式化日期时间
     */
    function format_date(date_str) {
        if (!date_str) return '';
        const date = new Date(date_str);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    /**
     * 格式化文件大小
     */
    function format_file_size(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * HTML 转义（防止 XSS）
     */
    function escape_html(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 生成唯一 ID
     */
    function generate_id() {
        return 'id_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * 深度复制对象
     */
    function deep_clone(obj) {
        if (obj === null || typeof obj !== 'object') {
            return obj;
        }
        if (Array.isArray(obj)) {
            return obj.map(deep_clone);
        }
        const cloned = {};
        for (let key in obj) {
            if (obj.hasOwnProperty(key)) {
                cloned[key] = deep_clone(obj[key]);
            }
        }
        return cloned;
    }

    /**
     * 防抖函数
     */
    function debounce(func, delay) {
        let timeout_id;
        return function(...args) {
            clearTimeout(timeout_id);
            timeout_id = setTimeout(() => func.apply(this, args), delay);
        };
    }

    /**
     * 节流函数
     */
    function throttle(func, limit) {
        let in_throttle;
        return function(...args) {
            if (!in_throttle) {
                func.apply(this, args);
                in_throttle = true;
                setTimeout(() => in_throttle = false, limit);
            }
        };
    }

    /**
     * 本地存储封装
     */
    const storage = {
        get: function(key) {
            try {
                const value = localStorage.getItem(key);
                return value ? JSON.parse(value) : null;
            } catch (e) {
                console.error('localStorage get error:', e);
                return null;
            }
        },
        set: function(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
            } catch (e) {
                console.error('localStorage set error:', e);
            }
        },
        remove: function(key) {
            try {
                localStorage.removeItem(key);
            } catch (e) {
                console.error('localStorage remove error:', e);
            }
        },
        clear: function() {
            try {
                localStorage.clear();
            } catch (e) {
                console.error('localStorage clear error:', e);
            }
        }
    };

    /**
     * URL 参数解析
     */
    function get_query_param(name, url) {
        url = url || window.location.href;
        const regex = new RegExp('[?&]' + name + '=([^&#]*)');
        const results = regex.exec(url);
        return results ? decodeURIComponent(results[1]) : null;
    }

    /**
     * 构建 URL 参数
     */
    function build_query_params(params) {
        const pairs = [];
        for (const key in params) {
            if (params.hasOwnProperty(key) && params[key] !== null && params[key] !== undefined) {
                pairs.push(encodeURIComponent(key) + '=' + encodeURIComponent(params[key]));
            }
        }
        return pairs.join('&');
    }

    /**
     * 显示 Toast 消息
     */
    function show_toast(message, type) {
        type = type || 'info';

        const container = document.getElementById('toast-container');
        if (!container) {
            console.warn('toast-container not found');
            return;
        }

        const toast = document.createElement('div');
        toast.className = 'toast toast-' + type;
        toast.textContent = message;

        container.appendChild(toast);

        // 触发动画
        setTimeout(function() {
            toast.classList.add('show');
        }, 10);

        // 自动消失
        setTimeout(function() {
            toast.classList.remove('show');
            setTimeout(function() {
                if (container.contains(toast)) {
                    container.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }

    /**
     * 确认对话框
     */
    function confirm_action(message, callback) {
        if (confirm(message)) {
            callback();
        }
    }

    /**
     * 状态文本映射
     */
    const status_text_map = {
        // 项目状态
        'in_progress': '进行中',
        'completed': '已完成',
        'ignored': '已挂起',

        // 里程碑状态
        'created': '已创建',
        'waiting': '等待中',
        'paused': '已暂停',
        'completed': '已完成',

        // 里程碑类型
        'milestone': '里程碑',
        'acceptance': '验收目标'
    };

    function get_status_text(status) {
        return status_text_map[status] || status;
    }

    /**
     * 状态 CSS 类名映射
     */
    const status_class_map = {
        'in_progress': 'status-in-progress',
        'completed': 'status-completed',
        'ignored': 'status-paused',
        'created': 'status-in-progress',
        'waiting': 'status-in-progress',
        'paused': 'status-paused'
    };

    function get_status_class(status) {
        return status_class_map[status] || '';
    }

    // ==================== 导出 ====================

    window.YWUtils = {
        // 格式化
        format_date: format_date,
        format_file_size: format_file_size,
        escape_html: escape_html,

        // 工具
        generate_id: generate_id,
        deep_clone: deep_clone,
        debounce: debounce,
        throttle: throttle,
        get_query_param: get_query_param,
        build_query_params: build_query_params,

        // 状态
        get_status_text: get_status_text,
        get_status_class: get_status_class,

        // 存储
        storage: storage,

        // UI
        show_toast: show_toast,
        confirm_action: confirm_action
    };

    // 兼容旧版本
    window.format_date = format_date;
    window.format_file_size = format_file_size;
    window.escape_html = escape_html;
    window.show_toast = show_toast;

    console.log('[INFO] utils.js 加载完成');
})();
