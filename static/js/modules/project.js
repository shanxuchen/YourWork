/**
 * YourWork - 项目管理模块
 * 处理项目列表、详情、创建等逻辑
 */

(function() {
    'use strict';

    /**
     * 加载项目列表
     */
    async function load_projects(params) {
        try {
            const result = await API.project.get_projects(params);

            if (result.code === 0) {
                return {
                    success: true,
                    data: result.data.items,
                    total: result.data.total
                };
            } else {
                YWUtils.show_toast(result.message, 'error');
                return { success: false };
            }
        } catch (e) {
            console.log('[Project] 加载项目列表失败:', e);
            YWUtils.show_toast('加载失败，请重试', 'error');
            return { success: false };
        }
    }

    /**
     * 加载项目详情
     */
    async function load_project_detail(project_id) {
        try {
            const result = await API.project.get_project(project_id);

            if (result.code === 0) {
                return {
                    success: true,
                    project: result.data.project,
                    milestones: result.data.milestones,
                    members: result.data.members,
                    deliverables: result.data.deliverables
                };
            } else {
                YWUtils.show_toast(result.message, 'error');
                return { success: false };
            }
        } catch (e) {
            console.log('[Project] 加载项目详情失败:', e);
            YWUtils.show_toast('加载失败，请重试', 'error');
            return { success: false };
        }
    }

    /**
     * 创建项目
     */
    async function create_project(name, description) {
        try {
            const result = await API.project.create_project(name, description);

            if (result.code === 0) {
                YWUtils.show_toast('项目创建成功', 'success');
                return {
                    success: true,
                    project_id: result.data.project_id,
                    project_no: result.data.project_no
                };
            } else {
                YWUtils.show_toast(result.message, 'error');
                return { success: false };
            }
        } catch (e) {
            console.log('[Project] 创建项目失败:', e);
            YWUtils.show_toast('创建失败，请重试', 'error');
            return { success: false };
        }
    }

    /**
     * 更新项目
     */
    async function update_project(project_id, name, description) {
        try {
            const result = await API.project.update_project(project_id, name, description);

            if (result.code === 0) {
                YWUtils.show_toast('更新成功', 'success');
                return { success: true };
            } else {
                YWUtils.show_toast(result.message, 'error');
                return { success: false };
            }
        } catch (e) {
            console.log('[Project] 更新项目失败:', e);
            YWUtils.show_toast('更新失败，请重试', 'error');
            return { success: false };
        }
    }

    /**
     * 更新项目状态
     */
    async function update_status(project_id, status) {
        try {
            const result = await API.project.update_status(project_id, status);

            if (result.code === 0) {
                YWUtils.show_toast('状态更新成功', 'success');
                return { success: true };
            } else {
                YWUtils.show_toast(result.message, 'error');
                return { success: false };
            }
        } catch (e) {
            console.log('[Project] 更新状态失败:', e);
            YWUtils.show_toast('更新失败，请重试', 'error');
            return { success: false };
        }
    }

    /**
     * 添加项目成员
     */
    async function add_member(project_id, user_id, display_name, roles) {
        try {
            const result = await API.project.add_member(project_id, user_id, display_name, roles);

            if (result.code === 0) {
                YWUtils.show_toast('成员添加成功', 'success');
                return { success: true };
            } else {
                YWUtils.show_toast(result.message, 'error');
                return { success: false };
            }
        } catch (e) {
            console.log('[Project] 添加成员失败:', e);
            YWUtils.show_toast('添加失败，请重试', 'error');
            return { success: false };
        }
    }

    /**
     * 移除项目成员
     */
    async function remove_member(project_id, user_id) {
        if (!confirm('确定要移除该成员吗？')) {
            return { success: false };
        }

        try {
            const result = await API.project.remove_member(project_id, user_id);

            if (result.code === 0) {
                YWUtils.show_toast('成员移除成功', 'success');
                return { success: true };
            } else {
                YWUtils.show_toast(result.message, 'error');
                return { success: false };
            }
        } catch (e) {
            console.log('[Project] 移除成员失败:', e);
            YWUtils.show_toast('移除失败，请重试', 'error');
            return { success: false };
        }
    }

    /**
     * 渲染项目列表
     */
    function render_project_list(projects, container_id) {
        const container = document.getElementById(container_id);
        if (!container) return;

        if (projects.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无项目</div>';
            return;
        }

        container.innerHTML = projects.map(function(p) {
            const status_class = YWUtils.get_status_class(p.status);
            const status_text = YWUtils.get_status_text(p.status);

            return `
                <div class="project-card" onclick="location.href='/projects/${p.id}'">
                    <div class="project-card-header">
                        <h3>${YWUtils.escape_html(p.name)}</h3>
                        <span class="status-badge ${status_class}">${status_text}</span>
                    </div>
                    <p class="project-card-no">编号: ${YWUtils.escape_html(p.project_no)}</p>
                    ${p.description ? `<p class="project-card-desc">${YWUtils.escape_html(p.description)}</p>` : ''}
                    <p class="project-card-time">创建于: ${YWUtils.format_date(p.created_at)}</p>
                </div>
            `;
        }).join('');
    }

    /**
     * 渲染状态标签
     */
    function render_status_select(current_status, select_id) {
        const select = document.getElementById(select_id);
        if (!select) return;

        const statuses = [
            { value: 'in_progress', text: '进行中' },
            { value: 'completed', text: '已完成' },
            { value: 'ignored', text: '已挂起' }
        ];

        select.innerHTML = statuses.map(function(s) {
            const selected = s.value === current_status ? ' selected' : '';
            return `<option value="${s.value}"${selected}>${s.text}</option>`;
        }).join('');
    }

    // 导出
    window.ProjectModule = {
        load_projects: load_projects,
        load_project_detail: load_project_detail,
        create_project: create_project,
        update_project: update_project,
        update_status: update_status,
        add_member: add_member,
        remove_member: remove_member,
        render_project_list: render_project_list,
        render_status_select: render_status_select
    };

    console.log('[INFO] project.js 加载完成');
})();
