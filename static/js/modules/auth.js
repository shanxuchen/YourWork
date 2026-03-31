/**
 * YourWork - 认证模块
 * 处理用户登录相关逻辑（内部系统，不允许自主注册）
 */

(function() {
    'use strict';

    // 当前登录用户
    let current_user = null;
    let user_roles = [];

    /**
     * 初始化认证状态
     */
    async function init_auth() {
        try {
            const result = await API.auth.get_profile();
            if (result.code === 0) {
                current_user = result.data;
                user_roles = result.data.roles || [];
                console.log('[Auth] 用户已登录:', current_user.username);
                return current_user;
            }
        } catch (e) {
            console.log('[Auth] 未登录或会话过期');
        }
        return null;
    }

    /**
     * 用户登录
     */
    async function login(username, password) {
        try {
            const result = await API.auth.login(username, password);

            if (result.code === 0) {
                current_user = result.data;
                console.log('[Auth] 登录成功');
                return { success: true, data: result.data };
            } else {
                console.log('[Auth] 登录失败:', result.message);
                return { success: false, message: result.message };
            }
        } catch (e) {
            console.log('[Auth] 登录异常:', e);
            return { success: false, message: '网络错误，请重试' };
        }
    }

    /**
     * 用户登出
     */
    async function logout() {
        try {
            await API.auth.logout();
        } catch (e) {
            console.log('[Auth] 登出请求失败:', e);
        }

        current_user = null;
        user_roles = [];

        console.log('[Auth] 已登出');
        window.location.href = '/login';
    }

    /**
     * 获取当前用户
     */
    function get_current_user() {
        return current_user;
    }

    /**
     * 检查是否有指定角色
     */
    function has_role(role_code) {
        return user_roles.some(function(r) {
            return r.code === role_code;
        });
    }

    /**
     * 检查是否是管理员
     */
    function is_admin() {
        return has_role('ADMIN') || has_role('SYSTEM_ADMIN');
    }

    /**
     * 获取用户显示名称
     */
    function get_display_name() {
        if (!current_user) return '';
        return current_user.display_name || current_user.username;
    }

    /**
     * 确保已登录，否则跳转到登录页
     */
    async function require_login() {
        const user = await init_auth();
        if (!user) {
            window.location.href = '/login';
            return false;
        }
        return true;
    }

    /**
     * 确保有管理员权限，否则显示提示
     */
    function require_admin() {
        if (!is_admin()) {
            YWUtils.show_toast('需要管理员权限', 'error');
            return false;
        }
        return true;
    }

    // 导出
    window.AuthModule = {
        init: init_auth,
        login: login,
        logout: logout,
        get_current_user: get_current_user,
        has_role: has_role,
        is_admin: is_admin,
        get_display_name: get_display_name,
        require_login: require_login,
        require_admin: require_admin
    };

    console.log('[INFO] auth.js 加载完成（内部系统，不允许自主注册）');
})();
