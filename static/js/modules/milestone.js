/**
 * YourWork - 里程碑管理模块
 * 处理里程碑的创建、更新、日志记录等逻辑
 */

(function() {
    'use strict';

    /**
     * 加载里程碑列表
     */
    async function load_milestones(project_id) {
        try {
            const result = await API.milestone.get_milestones(project_id);

            if (result.code === 0) {
                return {
                    success: true,
                    data: result.data
                };
            } else {
                YWUtils.show_toast(result.message, 'error');
                return { success: false };
            }
        } catch (e) {
            console.log('[Milestone] 加载里程碑列表失败:', e);
            YWUtils.show_toast('加载失败，请重试', 'error');
            return { success: false };
        }
    }

    /**
     * 加载里程碑详情
     */
    async function load_milestone_detail(milestone_id) {
        try {
            const result = await API.milestone.get_milestone(milestone_id);

            if (result.code === 0) {
                return {
                    success: true,
                    data: result.data
                };
            } else {
                YWUtils.show_toast(result.message, 'error');
                return { success: false };
            }
        } catch (e) {
            console.log('[Milestone] 加载里程碑详情失败:', e);
            YWUtils.show_toast('加载失败，请重试', 'error');
            return { success: false };
        }
    }

    /**
     * 创建里程碑
     */
    async function create_milestone(project_id, name, description, type, deadline) {
        try {
            const result = await API.milestone.create_milestone(project_id, name, description, type, deadline);

            if (result.code === 0) {
                YWUtils.show_toast('里程碑创建成功', 'success');
                return {
                    success: true,
                    milestone_id: result.data.milestone_id
                };
            } else {
                YWUtils.show_toast(result.message, 'error');
                return { success: false };
            }
        } catch (e) {
            console.log('[Milestone] 创建里程碑失败:', e);
            YWUtils.show_toast('创建失败，请重试', 'error');
            return { success: false };
        }
    }

    /**
     * 更新里程碑
     */
    async function update_milestone(milestone_id, name, description, status) {
        try {
            const result = await API.milestone.update_milestone(milestone_id, name, description, status);

            if (result.code === 0) {
                YWUtils.show_toast('更新成功', 'success');
                return { success: true };
            } else {
                YWUtils.show_toast(result.message, 'error');
                return { success: false };
            }
        } catch (e) {
            console.log('[Milestone] 更新里程碑失败:', e);
            YWUtils.show_toast('更新失败，请重试', 'error');
            return { success: false };
        }
    }

    /**
     * 加载操作日志
     */
    async function load_logs(milestone_id) {
        try {
            const result = await API.milestone.get_logs(milestone_id);

            if (result.code === 0) {
                return {
                    success: true,
                    data: result.data
                };
            } else {
                return { success: false };
            }
        } catch (e) {
            console.log('[Milestone] 加载日志失败:', e);
            return { success: false };
        }
    }

    /**
     * 添加操作日志
     */
    async function add_log(milestone_id, action, description) {
        try {
            const result = await API.milestone.add_log(milestone_id, action, description);

            if (result.code === 0) {
                return { success: true };
            } else {
                YWUtils.show_toast(result.message, 'error');
                return { success: false };
            }
        } catch (e) {
            console.log('[Milestone] 添加日志失败:', e);
            return { success: false };
        }
    }

    /**
     * 渲染里程碑列表
     */
    function render_milestone_list(milestones, container_id) {
        const container = document.getElementById(container_id);
        if (!container) return;

        if (milestones.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无里程碑</div>';
            return;
        }

        container.innerHTML = milestones.map(function(m) {
            const status_class = YWUtils.get_status_class(m.status);
            const status_text = YWUtils.get_status_text(m.status);
            const type_class = m.type === 'milestone' ? 'type-milestone' : 'type-acceptance';
            const type_text = m.type === 'milestone' ? '里程碑' : '验收目标';

            return `
                <div class="milestone-card" data-id="${m.id}">
                    <div class="milestone-card-header">
                        <span class="milestone-type ${type_class}">${type_text}</span>
                        <span class="status-badge ${status_class}">${status_text}</span>
                    </div>
                    <h4>${YWUtils.escape_html(m.name)}</h4>
                    ${m.description ? `<p class="milestone-desc">${YWUtils.escape_html(m.description)}</p>` : ''}
                    ${m.deadline ? `<p class="milestone-deadline">截止: ${YWUtils.format_date(m.deadline)}</p>` : ''}
                </div>
            `;
        }).join('');
    }

    /**
     * 渲染操作日志
     */
    function render_logs(logs, container_id) {
        const container = document.getElementById(container_id);
        if (!container) return;

        if (logs.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无操作记录</div>';
            return;
        }

        container.innerHTML = logs.map(function(log) {
            return `
                <div class="log-item">
                    <div class="log-header">
                        <span class="log-action">${YWUtils.escape_html(log.action)}</span>
                        <span class="log-time">${YWUtils.format_date(log.created_at)}</span>
                    </div>
                    ${log.description ? `<p class="log-desc">${YWUtils.escape_html(log.description)}</p>` : ''}
                    <p class="log-user">操作人: ${YWUtils.escape_html(log.username)}</p>
                </div>
            `;
        }).join('');
    }

    /**
     * 获取状态选项
     */
    function get_status_options() {
        return [
            { value: 'created', text: '已创建' },
            { value: 'waiting', text: '等待中' },
            { value: 'paused', text: '已暂停' },
            { value: 'completed', text: '已完成' }
        ];
    }

    // 导出
    window.MilestoneModule = {
        load_milestones: load_milestones,
        load_milestone_detail: load_milestone_detail,
        create_milestone: create_milestone,
        update_milestone: update_milestone,
        load_logs: load_logs,
        add_log: add_log,
        render_milestone_list: render_milestone_list,
        render_logs: render_logs,
        get_status_options: get_status_options
    };

    console.log('[INFO] milestone.js 加载完成');
})();
