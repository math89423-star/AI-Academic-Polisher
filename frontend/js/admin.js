document.addEventListener('DOMContentLoaded', () => {
    let currentAdmin = localStorage.getItem('admin_username');
    let globalApiConfigs = []; 

    const loginContainer = document.getElementById('admin-login-container');
    const dashboard = document.getElementById('admin-dashboard');
    const roleSelect = document.getElementById('new-role');
    const pwdGroup = document.getElementById('pwd-group');

    roleSelect.addEventListener('change', (e) => {
        pwdGroup.style.display = e.target.value === 'admin' ? 'block' : 'none';
    });
    pwdGroup.style.display = 'none';

    if (currentAdmin) {
        showDashboard();
    }

    // --- 登录模块 ---
    document.getElementById('admin-login-btn').addEventListener('click', async () => {
        const username = document.getElementById('admin-username').value;
        const password = document.getElementById('admin-password').value;
        const msgBox = document.getElementById('admin-login-msg');
        
        try {
            const res = await fetch('/api/auth/login/admin', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const data = await res.json();
            if (res.ok) {
                localStorage.setItem('admin_username', data.username);
                currentAdmin = data.username;
                showDashboard();
            } else {
                msgBox.innerText = data.error || "登录失败";
            }
        } catch (err) {
            msgBox.innerText = "网络连接失败";
        }
    });

    document.getElementById('admin-logout-btn').addEventListener('click', () => {
        localStorage.removeItem('admin_username');
        location.reload();
    });

    async function showDashboard() {
        loginContainer.classList.add('hidden');
        dashboard.classList.remove('hidden');
        document.getElementById('current-admin-name').innerText = currentAdmin;
        
        // 必须加 await，确保先拿到线路数据，再去渲染用户列表里的下拉框
        await loadApiConfigs();
        loadUsers();
    }

    // --- 线路与用户加载逻辑 ---
    async function loadApiConfigs() {
        const res = await fetch(`/api/admin/api_configs?admin_username=${currentAdmin}`);
        if (res.ok) {
            globalApiConfigs = await res.json();
            
            // 1. 渲染用户表单的下拉框
            const select = document.getElementById('new-user-api-config');
            select.innerHTML = '<option value="">(继承系统默认全局线路)</option>';
            globalApiConfigs.forEach(conf => {
                select.innerHTML += `<option value="${conf.id}">${conf.name} (${conf.model_name})</option>`;
            });

            // 2. 渲染大模型线路调度池表格
            const tbody = document.getElementById('api-table-body');
            tbody.innerHTML = '';
            globalApiConfigs.forEach(conf => {
                tbody.innerHTML += `
                    <tr>
                        <td style="font-weight: 500; color: #0f172a;">${conf.name}</td>
                        <td><span style="background: #f1f5f9; padding: 4px 8px; border-radius: 4px; font-size: 12px; color: #3b82f6;">${conf.model_name}</span></td>
                        <td style="color: #64748b; font-size: 13px;">${conf.base_url}</td>
                        <td>
                            <button class="delete-api-btn" data-target="${conf.id}" style="background: #ef4444; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; transition: 0.2s;">销毁线路</button>
                        </td>
                    </tr>
                `;
            });

            // 绑定删除线路事件
            document.querySelectorAll('.delete-api-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.target.getAttribute('data-target');
                    if (!confirm('🚨 警告：确定要彻底销毁该线路吗？\n正在使用该线路的用户将自动降级为系统默认配置！')) return;
                    
                    const delRes = await fetch(`/api/admin/api_configs/${id}?admin_username=${currentAdmin}`, { method: 'DELETE' });
                    if (delRes.ok) {
                        await loadApiConfigs();
                        loadUsers(); // 刷新用户列表以重置他们的下拉框状态
                    } else { alert("线路销毁失败"); }
                });
            });
        }
    }

    async function loadUsers() {
        const res = await fetch(`/api/admin/users?admin_username=${currentAdmin}`);
        if (!res.ok) return;
        const users = await res.json();
        
        const tbody = document.getElementById('user-table-body');
        tbody.innerHTML = '';
        
        users.forEach(u => {
            let optionsHtml = '<option value="">[默认] 系统全局线路</option>';
            globalApiConfigs.forEach(conf => {
                const selected = (u.api_config_id === conf.id) ? 'selected' : '';
                optionsHtml += `<option value="${conf.id}" ${selected}>${conf.name}</option>`;
            });

            const roleBadge = u.role === 'admin' 
                ? '<span class="role-badge role-admin">管理员</span>' 
                : '<span class="role-badge role-user">普通用户</span>';

            tbody.innerHTML += `
                <tr>
                    <td style="font-weight: 500; color: #0f172a;">${u.username}</td>
                    <td>${roleBadge}</td>
                    <td>
                        <select class="api-select" data-username="${u.username}">
                            ${optionsHtml}
                        </select>
                    </td>
                    <td><span style="background: #f1f5f9; padding: 2px 8px; border-radius: 4px;">${u.usage_count} 次</span></td>
                    <td>
                        <button class="delete-btn" data-target="${u.username}">彻底删除</button>
                    </td>
                </tr>
            `;
        });

        // 绑定更新用户线路事件
        document.querySelectorAll('.api-select').forEach(select => {
            select.addEventListener('change', async (e) => {
                const target_username = e.target.getAttribute('data-username');
                const api_config_id = e.target.value;
                const res = await fetch('/api/admin/users/update_config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ admin_username: currentAdmin, target_username, api_config_id })
                });
                if (!res.ok) alert("调度线路更新失败，请检查权限");
            });
        });

        // 绑定删除用户事件
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const target = e.target.getAttribute('data-target');
                if (!confirm(`🚨 危险操作！\n\n确定要彻底删除用户 [${target}] 吗？\n该用户产生的所有历史记录将不可恢复！`)) return;

                const res = await fetch(`/api/admin/users/${target}?admin_username=${currentAdmin}`, {
                    method: 'DELETE'
                });
                if (res.ok) loadUsers();
                else alert("删除失败");
            });
        });
    }

    // --- 按钮提交事件 ---
    document.getElementById('add-user-btn').addEventListener('click', async () => {
        const new_username = document.getElementById('new-username').value;
        const role = document.getElementById('new-role').value;
        const password = document.getElementById('new-password').value;
        const api_config_id = document.getElementById('new-user-api-config').value;

        if (!new_username) return alert("请输入用户名！");
        if (role === 'admin' && !password) return alert("管理员账号必须设置安全密码！");

        const btn = document.getElementById('add-user-btn');
        btn.disabled = true;
        btn.innerText = "创建中...";

        try {
            const res = await fetch('/api/admin/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ admin_username: currentAdmin, new_username, role, password, api_config_id })
            });
            
            if (res.ok) {
                document.getElementById('new-username').value = '';
                document.getElementById('new-password').value = '';
                loadUsers();
            } else {
                let errorMsg = "创建失败";
                try {
                    const data = await res.json();
                    errorMsg = data.error || errorMsg;
                } catch(e) {}
                alert(errorMsg);
            }
        } catch (err) {
            alert("请求超时或服务器无响应，请重试");
        } finally {
            btn.disabled = false;
            btn.innerText = "生成并分配账号";
        }
    });

    // 🟢 绑定新增大模型线路事件
    document.getElementById('add-api-btn').addEventListener('click', async () => {
        const name = document.getElementById('new-api-name').value.trim();
        const base_url = document.getElementById('new-api-base-url').value.trim();
        const api_key = document.getElementById('new-api-key').value.trim();
        const model_name = document.getElementById('new-api-model').value.trim();

        if (!name || !base_url || !api_key || !model_name) return alert("请完整填写所有线路配置信息！");

        const btn = document.getElementById('add-api-btn');
        btn.disabled = true; 
        btn.innerText = "正在注册线路...";

        try {
            const res = await fetch('/api/admin/api_configs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ admin_username: currentAdmin, name, base_url, api_key, model_name })
            });

            if (res.ok) {
                document.getElementById('new-api-name').value = '';
                document.getElementById('new-api-base-url').value = '';
                document.getElementById('new-api-key').value = '';
                document.getElementById('new-api-model').value = '';
                await loadApiConfigs(); // 刷新线路表格
                loadUsers(); // 刷新用户列表中的下拉选项
            } else {
                let errorMsg = "创建线路失败";
                try {
                    const data = await res.json();
                    errorMsg = data.error || errorMsg;
                } catch(e) {}
                alert(errorMsg);
            }
        } catch (err) { alert("网络错误，请求失败"); } 
        finally {
            btn.disabled = false; 
            btn.innerText = "启用新线路";
        }
    });
});