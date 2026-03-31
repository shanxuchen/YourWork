/**
 * YourWork - 消息管理模块
 * 处理消息列表、未读数量、标记已读等逻辑
 */

(function() {
    'use strict';

    let unread_count = 0;

    /**
     * 加载消息列表
     */
    async function load_messages(params) {
        try {
            const result = await API.message.get_messages(params);

            if (result.code === 0) {
                unread_count = result.data.unread_count;
                return {
                    success: true,
                    items: result.data.items,
                    total: result.data.total,
                    unread_count: unread_count
                };
            } else {
                YWUtils.show_toast(result.message, 'error');
                return { success: false };
            }
        } catch (e) {
            console.log('[Message] 加载消息列表失败:', e);
            YWUtils.show_toast('加载失败，请重试', 'error');
            return { success: false };
        }
    }

    /**
     * 刷新未读数量
     */
    async function refresh_unread_count() {
        try {
            const result = await API.message.get_unread_count();

            if (result.code === 0) {
                unread_count = result.data.unread_count;
                update_unread_display();
                return { success: true, count: unread_count };
            }
        } catch (e) {
            console.log('[Message] 获取未读数量失败:', e);
        }
        return { success: false };
    }

    /**
     * 标记消息为已读
     */
    async function mark_read(message_id) {
        try {
            const result = await API.message.mark_read(message_id);

            if (result.code === 0) {
                if (unread_count > 0) {
                    unread_count--;
                    update_unread_display();
                }
                return { success: true };
            }
        } catch (e) {
            console.log('[Message] 标记已读失败:', e);
        }
        return { success: false };
    }

    /**
     * 全部标记为已读
     */
    async function mark_all_read() {
        try {
            const result = await API.message.mark_all_read();

            if (result.code === 0) {
                unread_count = 0;
                update_unread_display();
                YWUtils.show_toast('已全部标记为已读', 'success');
                return { success: true };
            } else {
                YWUtils.show_toast(result.message, 'error');
                return { success: false };
            }
        } catch (e) {
            console.log('[Message] 全部标记已读失败:', e);
            YWUtils.show_toast('操作失败，请重试', 'error');
            return { success: false };
        }
    }

    /**
     * 删除消息
     */
    async function delete_message(message_id) {
        if (!confirm('确定要删除这条消息吗？')) {
            return { success: false };
        }

        try {
            const result = await API.message.delete(message_id);

            if (result.code === 0) {
                YWUtils.show_toast('消息已删除', 'success');
                return { success: true };
            } else {
                YWUtils.show_toast(result.message, 'error');
                return { success: false };
            }
        } catch (e) {
            console.log('[Message] 删除消息失败:', e);
            YWUtils.show_toast('删除失败，请重试', 'error');
            return { success: false };
        }
    }

    /**
     * 更新未读数量显示
     */
    function update_unread_display() {
        const badges = document.querySelectorAll('.message-unread-badge');
        badges.forEach(function(badge) {
            if (unread_count > 0) {
                badge.textContent = unread_count > 99 ? '99+' : unread_count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        });
    }

    /**
     * 渲染消息列表
     */
    function render_message_list(messages, container_id) {
        const container = document.getElementById(container_id);
        if (!container) return;

        if (messages.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无消息</div>';
            return;
        }

        container.innerHTML = messages.map(function(m) {
            const unread_class = m.is_read ? '' : ' unread';
            const type_class = 'type-' + m.type;

            return `
                <div class="message-item${unread_class}" data-id="${m.id}">
                    <div class="message-header">
                        <span class="message-type ${type_class}">${get_type_text(m.type)}</span>
                        <span class="message-time">${YWUtils.format_date(m.created_at)}</span>
                    </div>
                    <h4 class="message-title">${YWUtils.escape_html(m.title)}</h4>
                    ${m.content ? `<p class="message-content">${YWUtils.escape_html(m.content)}</p>` : ''}
                </div>
            `;
        }).join('');
    }

    /**
     * 获取消息类型文本
     */
    function get_type_text(type) {
        const types = {
            'system': '系统',
            'project': '项目',
            'milestone': '里程碑',
            'reminder': '提醒'
        };
        return types[type] || type;
    }

    /**
     * 获取未读数量
     */
    function get_unread_count() {
        return unread_count;
    }

    // 导出
    window.MessageModule = {
        load_messages: load_messages,
        refresh_unread_count: refresh_unread_count,
        mark_read: mark_read,
        mark_all_read: mark_all_read,
        delete_message: delete_message,
        render_message_list: render_message_list,
        get_unread_count: get_unread_count
    };

    console.log('[INFO] message.js 加载完成');
})();
