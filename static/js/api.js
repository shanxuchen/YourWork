/**
 * YourWork - API 封装
 * 使用原生 Fetch API（浏览器内置）
 */

(function() {
    'use strict';

    // API 基础路径
    const API_BASE = '/api/v1';

    /**
     * 日志函数
     */
    function log_api(level, message, data) {
        const time = new Date().toTimeString().split(' ')[0];
        const prefix = `[API] [${level}] ${time} |`;

        if (data !== undefined) {
            console.log(prefix, message, data);
        } else {
            console.log(prefix, message);
        }
    }

    /**
     * 通用请求函数
     */
    async function request(method, endpoint, options) {
        const url = API_BASE + endpoint;
        const body = options?.body;
        const is_form_data = body instanceof FormData;

        log_api('INFO', `${method} ${endpoint}`, is_form_data ? '<FormData>' : body);

        const start_time = Date.now();

        try {
            const response = await fetch(url, {
                method: method,
                headers: is_form_data ? undefined : {
                    'Content-Type': 'application/json',
                    ...(options?.headers || {})
                },
                body: is_form_data ? body : (body ? JSON.stringify(body) : undefined)
            });

            const duration = Date.now() - start_time;

            // 尝试解析 JSON
            let data;
            const content_type = response.headers.get('content-type');
            if (content_type && content_type.includes('application/json')) {
                data = await response.json();
            } else {
                data = await response.text();
            }

            log_api('INFO', `响应 ${endpoint} [${response.status}] (${duration}ms)`, data);

            // 处理 401 未登录
            if (response.status === 401 && window.location.pathname !== '/login') {
                log_api('WARNING', '未登录，跳转到登录页');
                window.location.href = '/login';
                return data;
            }

            return data;
        } catch (error) {
            log_api('ERROR', `请求失败: ${endpoint}`, error);
            throw error;
        }
    }

    /**
     * GET 请求
     */
    async function api_get(endpoint, options) {
        return request('GET', endpoint, options);
    }

    /**
     * POST 请求
     */
    async function api_post(endpoint, body, options) {
        return request('POST', endpoint, { ...options, body });
    }

    /**
     * PUT 请求
     */
    async function api_put(endpoint, body, options) {
        return request('PUT', endpoint, { ...options, body });
    }

    /**
     * DELETE 请求
     */
    async function api_delete(endpoint, options) {
        return request('DELETE', endpoint, options);
    }

    /**
     * 文件上传
     */
    async function api_upload(endpoint, form_data, options) {
        return request('POST', endpoint, { ...options, body: form_data });
    }

    // ==================== API 方法封装 ====================

    /**
     * 认证模块
     */
    const AuthAPI = {
        // 登录
        login: function(username, password) {
            return api_post('/auth/login', { username, password });
        },

        // 登出
        logout: function() {
            return api_post('/auth/logout');
        },

        // 获取当前用户信息
        get_profile: function() {
            return api_get('/auth/profile');
        }
    };

    /**
     * 用户管理模块
     */
    const UserAPI = {
        // 获取用户列表
        get_users: function() {
            return api_get('/users');
        },

        // 更新用户角色
        update_user_roles: function(user_id, roles) {
            return api_put(`/users/${user_id}/roles`, { roles });
        }
    };

    /**
     * 项目管理模块
     */
    const ProjectAPI = {
        // 获取项目列表
        get_projects: function(params) {
            const query = params ? '?' + YWUtils.build_query_params(params) : '';
            return api_get('/projects' + query);
        },

        // 获取项目详情
        get_project: function(project_id) {
            return api_get(`/projects/${project_id}`);
        },

        // 创建项目
        create_project: function(name, description) {
            return api_post('/projects', { name, description });
        },

        // 更新项目
        update_project: function(project_id, name, description) {
            return api_put(`/projects/${project_id}`, { name, description });
        },

        // 更新项目状态
        update_status: function(project_id, status) {
            return api_put(`/projects/${project_id}/status`, { status });
        },

        // 添加成员
        add_member: function(project_id, user_id, display_name, roles) {
            return api_post(`/projects/${project_id}/members`, { user_id, display_name, roles });
        },

        // 移除成员
        remove_member: function(project_id, user_id) {
            return request('DELETE', `/projects/${project_id}/members/${user_id}`);
        },

        // 获取产出物列表
        get_deliverables: function(project_id, milestone_id) {
            const query = milestone_id ? `?milestone_id=${milestone_id}` : '';
            return api_get(`/projects/${project_id}/deliverables` + query);
        },

        // 上传产出物
        upload_deliverable: function(project_id, form_data, milestone_id) {
            const query = milestone_id ? `?milestone_id=${milestone_id}` : '';
            return api_upload(`/projects/${project_id}/deliverables/upload` + query, form_data);
        }
    };

    /**
     * 里程碑管理模块
     */
    const MilestoneAPI = {
        // 获取项目里程碑列表
        get_milestones: function(project_id) {
            return api_get(`/projects/${project_id}/milestones`);
        },

        // 获取里程碑详情
        get_milestone: function(milestone_id) {
            return api_get(`/milestones/${milestone_id}`);
        },

        // 创建里程碑
        create_milestone: function(project_id, name, description, type, deadline) {
            return api_post('/milestones', { project_id, name, description, type, deadline });
        },

        // 更新里程碑
        update_milestone: function(milestone_id, name, description, status) {
            return api_put(`/milestones/${milestone_id}`, { name, description, status });
        },

        // 获取操作日志
        get_logs: function(milestone_id) {
            return api_get(`/milestones/${milestone_id}/logs`);
        },

        // 添加操作日志
        add_log: function(milestone_id, action, description) {
            return api_post(`/milestones/${milestone_id}/logs`, { action, description });
        }
    };

    /**
     * 产出物模块
     */
    const DeliverableAPI = {
        // 下载产出物
        download: function(deliverable_id) {
            window.location.href = `${API_BASE}/deliverables/${deliverable_id}/download`;
        }
    };

    /**
     * 消息管理模块
     */
    const MessageAPI = {
        // 获取消息列表
        get_messages: function(params) {
            const query = params ? '?' + YWUtils.build_query_params(params) : '';
            return api_get('/messages' + query);
        },

        // 获取未读数量
        get_unread_count: function() {
            return api_get('/messages/unread-count');
        },

        // 标记为已读
        mark_read: function(message_id) {
            return api_put(`/messages/${message_id}/read`);
        },

        // 全部标记为已读
        mark_all_read: function() {
            return api_put('/messages/read-all');
        },

        // 删除消息
        delete: function(message_id) {
            return request('DELETE', `/messages/${message_id}`);
        }
    };

    // ==================== 导出 ====================

    window.api_get = api_get;
    window.api_post = api_post;
    window.api_put = api_put;
    window.api_delete = api_delete;
    window.api_upload = api_upload;

    // API 模块
    window.API = {
        auth: AuthAPI,
        user: UserAPI,
        project: ProjectAPI,
        milestone: MilestoneAPI,
        deliverable: DeliverableAPI,
        message: MessageAPI
    };

    console.log('[INFO] api.js 加载完成');
})();
