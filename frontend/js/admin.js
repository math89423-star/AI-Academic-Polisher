document.addEventListener('DOMContentLoaded', () => {
    let currentAdmin = localStorage.getItem('admin_username');
    let globalApiConfigs = []; // 缓存全局线路列表，用于渲染用户表中的下拉框

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
            document.getElementById('admin-login-msg').innerText = data.error;
        }
    });

    document.getElementById('admin-logout-btn').addEventListener('click', () => {
        localStorage.removeItem('admin_username');
        location.reload();
    });

    function showDashboard() {
        loginContainer.classList.add('hidden');
        dashboard.classList.remove('hidden');
        loadApiConfigs(); 
        // 用户列表会在 loadApiConfigs 成功后被触发，确保下拉框有数据
    }


    // --- API 线路管理 ---
    async function loadApiConfigs() {
        const res = await fetch(`/api/admin/api_configs?username=${currentAdmin}`);
        if (!res.ok) return;
        globalApiConfigs = await res.json(); 
        
        const tbody = document.getElementById('api-table-body');
        tbody.innerHTML = '';
        const select = document.getElementById('new-user-api-config');
        select.innerHTML = ''; 

        globalApiConfigs.forEach(c => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>#${c.id}</td>
                <td><strong>${c.name}</strong></td>
                <td><span class="badge">${c.model_name}</span></td>
                <td style="color: gray; font-size: 12px;">${c.base_url}</td>
                <td>
                    <button class="text-btn delete-api-btn" data-id="${c.id}" data-name="${c.name}" style="color: #ef4444;">
                        🗑️ 删除
                    </button>
                </td>
            `;
            tbody.appendChild(tr);

            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            select.appendChild(opt);
        });

        // 🟢 绑定：删除线路事件
        document.querySelectorAll('.delete-api-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const targetId = e.currentTarget.getAttribute('data-id');
                const targetName = e.currentTarget.getAttribute('data-name');
                
                if (!confirm(`确定要删除线路 [${targetName}] 吗？\n注意：正在使用该线路的用户将自动退回“未分配”状态（使用全局默认线路）。`)) return;

                const res = await fetch(`/api/admin/api_configs/${targetId}?admin_username=${currentAdmin}`, {
                    method: 'DELETE'
                });
                
                if (res.ok) {
                    loadApiConfigs(); // 刷新线路表和用户表的下拉框
                } else {
                    const data = await res.json();
                    alert("删除失败: " + (data.error || "未知错误"));
                }
            });
        });

        loadUsers(); // 确保线路加载完后再渲染用户列表
    }

    document.getElementById('add-api-btn').addEventListener('click', async () => {
        const name = document.getElementById('new-api-name').value;
        const api_key = document.getElementById('new-api-key').value;
        const base_url = document.getElementById('new-api-url').value;
        const model_name = document.getElementById('new-api-model').value;

        await fetch('/api/admin/api_configs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ admin_username: currentAdmin, name, api_key, base_url, model_name })
        });
        loadApiConfigs();
    });

    // --- 用户管理模块 ---
    async function loadUsers() {
        const res = await fetch(`/api/admin/users?username=${currentAdmin}`);
        if (!res.ok) return;
        const users = await res.json();
        
        const tbody = document.getElementById('user-table-body');
        tbody.innerHTML = '';
        
        users.forEach(u => {
            const tr = document.createElement('tr');
            
            // 构建内联线路选择器
            let optionsHtml = globalApiConfigs.map(config => 
                `<option value="${config.id}" ${u.api_config_id === config.id ? 'selected' : ''}>${config.name}</option>`
            ).join('');

            tr.innerHTML = `
                <td><strong>${u.username}</strong></td>
                <td><span class="badge ${u.role}">${u.role === 'admin' ? '管理员' : '普通用户'}</span></td>
                <td>
                    <select class="api-config-selector" data-user="${u.username}">
                        ${optionsHtml}
                    </select>
                </td>
                <td>${u.usage_count} 次</td>
                <td>
                    <button class="text-btn delete-btn" data-target="${u.username}" style="color: #ef4444;">
                        🗑️ 删除
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        // 绑定：在线修改线路
        document.querySelectorAll('.api-config-selector').forEach(select => {
            select.addEventListener('change', async (e) => {
                const target_username = e.target.getAttribute('data-user');
                const new_config_id = e.target.value;
                
                const res = await fetch('/api/admin/users/update_config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        admin_username: currentAdmin,
                        target_username: target_username,
                        api_config_id: new_config_id
                    })
                });
                if (!res.ok) alert("修改线路失败");
            });
        });

        // 绑定：物理删除用户
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const target = e.target.getAttribute('data-target');
                if (!confirm(`确定要彻底删除用户 [${target}] 吗？该操作不可恢复。`)) return;

                const res = await fetch(`/api/admin/users/${target}?admin_username=${currentAdmin}`, {
                    method: 'DELETE'
                });
                if (res.ok) loadUsers();
                else alert("删除失败");
            });
        });
    }

    document.getElementById('add-user-btn').addEventListener('click', async () => {
        const new_username = document.getElementById('new-username').value;
        const role = document.getElementById('new-role').value;
        const password = document.getElementById('new-password').value;
        const api_config_id = document.getElementById('new-user-api-config').value;

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
            const data = await res.json();
            alert(data.error || "创建失败");
        }
    });
});