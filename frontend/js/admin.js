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
            // 标准模式下拉框
            let optionsStandard = '<option value="">[默认] 系统全局线路</option>';
            globalApiConfigs.forEach(conf => {
                const selected = (u.api_config_id_standard === conf.id) ? 'selected' : '';
                optionsStandard += `<option value="${conf.id}" ${selected}>${conf.name}</option>`;
            });

            // 极致模式下拉框
            let optionsStrict = '<option value="">[默认] 系统全局线路</option>';
            globalApiConfigs.forEach(conf => {
                const selected = (u.api_config_id_strict === conf.id) ? 'selected' : '';
                optionsStrict += `<option value="${conf.id}" ${selected}>${conf.name}</option>`;
            });

            const roleBadge = u.role === 'admin'
                ? '<span class="role-badge role-admin">管理员</span>'
                : '<span class="role-badge role-user">普通用户</span>';

            tbody.innerHTML += `
                <tr>
                    <td><input type="checkbox" class="user-checkbox" data-username="${u.username}"></td>
                    <td style="font-weight: 500; color: #0f172a;">${u.username}</td>
                    <td>${roleBadge}</td>
                    <td>
                        <select class="api-select" data-username="${u.username}" data-mode="standard">
                            ${optionsStandard}
                        </select>
                    </td>
                    <td>
                        <select class="api-select" data-username="${u.username}" data-mode="strict">
                            ${optionsStrict}
                        </select>
                    </td>
                    <td><span style="background: #f1f5f9; padding: 2px 8px; border-radius: 4px;">${u.usage_count} 次</span></td>
                    <td>
                        <button class="delete-btn" data-target="${u.username}">彻底删除</button>
                    </td>
                </tr>
            `;
        });

        // 绑定全选功能
        document.getElementById('select-all-users').addEventListener('change', (e) => {
            document.querySelectorAll('.user-checkbox').forEach(cb => {
                cb.checked = e.target.checked;
            });
            updateSelectedCount();
        });

        // 绑定复选框变化事件
        document.querySelectorAll('.user-checkbox').forEach(cb => {
            cb.addEventListener('change', updateSelectedCount);
        });

        // 绑定更新用户线路事件
        document.querySelectorAll('.api-select').forEach(select => {
            select.addEventListener('change', async (e) => {
                const target_username = e.target.getAttribute('data-username');
                const mode = e.target.getAttribute('data-mode');
                const api_config_id = e.target.value;
                const res = await fetch('/api/admin/users/update_config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ admin_username: currentAdmin, target_username, api_config_id, mode })
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

    function updateSelectedCount() {
        const count = document.querySelectorAll('.user-checkbox:checked').length;
        document.getElementById('selected-count').innerText = `已选择 ${count} 个用户`;
    }

    // 批量更新标准模式线路
    document.getElementById('batch-update-standard-btn').addEventListener('click', async () => {
        const selectedUsers = Array.from(document.querySelectorAll('.user-checkbox:checked'))
            .map(cb => cb.getAttribute('data-username'));

        if (selectedUsers.length === 0) {
            alert('请先选择要更新的用户');
            return;
        }

        // 构建线路选择对话框
        let options = '<option value="">使用系统默认线路</option>';
        globalApiConfigs.forEach(conf => {
            options += `<option value="${conf.id}">${conf.name} (${conf.model_name})</option>`;
        });

        const selectHtml = `
            <div style="padding: 20px;">
                <p style="margin-bottom: 15px;">为选中的 ${selectedUsers.length} 个用户批量设置<strong>标准模式</strong>线路：</p>
                <select id="batch-select-standard" style="width: 100%; padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;">
                    ${options}
                </select>
            </div>
        `;

        // 创建自定义对话框
        const dialog = document.createElement('div');
        dialog.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 9999;';
        dialog.innerHTML = `
            <div style="background: white; border-radius: 12px; width: 500px; max-width: 90%;">
                ${selectHtml}
                <div style="padding: 0 20px 20px; display: flex; gap: 10px; justify-content: flex-end;">
                    <button id="batch-cancel" style="padding: 10px 20px; background: #e2e8f0; border: none; border-radius: 6px; cursor: pointer;">取消</button>
                    <button id="batch-confirm" style="padding: 10px 20px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer;">确认更新</button>
                </div>
            </div>
        `;
        document.body.appendChild(dialog);

        document.getElementById('batch-cancel').onclick = () => dialog.remove();
        document.getElementById('batch-confirm').onclick = async () => {
            const api_config_id = document.getElementById('batch-select-standard').value;
            dialog.remove();

            const res = await fetch('/api/admin/users/batch_update_config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    admin_username: currentAdmin,
                    usernames: selectedUsers,
                    mode: 'standard',
                    api_config_id: api_config_id || null
                })
            });

            if (res.ok) {
                const data = await res.json();
                alert(data.message);
                loadUsers();
            } else {
                alert('批量更新失败');
            }
        };
    });

    // 批量更新极致模式线路
    document.getElementById('batch-update-strict-btn').addEventListener('click', async () => {
        const selectedUsers = Array.from(document.querySelectorAll('.user-checkbox:checked'))
            .map(cb => cb.getAttribute('data-username'));

        if (selectedUsers.length === 0) {
            alert('请先选择要更新的用户');
            return;
        }

        // 构建线路选择对话框
        let options = '<option value="">使用系统默认线路</option>';
        globalApiConfigs.forEach(conf => {
            options += `<option value="${conf.id}">${conf.name} (${conf.model_name})</option>`;
        });

        const selectHtml = `
            <div style="padding: 20px;">
                <p style="margin-bottom: 15px;">为选中的 ${selectedUsers.length} 个用户批量设置<strong>极致模式</strong>线路：</p>
                <select id="batch-select-strict" style="width: 100%; padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px;">
                    ${options}
                </select>
            </div>
        `;

        // 创建自定义对话框
        const dialog = document.createElement('div');
        dialog.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 9999;';
        dialog.innerHTML = `
            <div style="background: white; border-radius: 12px; width: 500px; max-width: 90%;">
                ${selectHtml}
                <div style="padding: 0 20px 20px; display: flex; gap: 10px; justify-content: flex-end;">
                    <button id="batch-cancel" style="padding: 10px 20px; background: #e2e8f0; border: none; border-radius: 6px; cursor: pointer;">取消</button>
                    <button id="batch-confirm" style="padding: 10px 20px; background: #8b5cf6; color: white; border: none; border-radius: 6px; cursor: pointer;">确认更新</button>
                </div>
            </div>
        `;
        document.body.appendChild(dialog);

        document.getElementById('batch-cancel').onclick = () => dialog.remove();
        document.getElementById('batch-confirm').onclick = async () => {
            const api_config_id = document.getElementById('batch-select-strict').value;
            dialog.remove();

            const res = await fetch('/api/admin/users/batch_update_config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    admin_username: currentAdmin,
                    usernames: selectedUsers,
                    mode: 'strict',
                    api_config_id: api_config_id || null
                })
            });

            if (res.ok) {
                const data = await res.json();
                alert(data.message);
                loadUsers();
            } else {
                alert('批量更新失败');
            }
        };
    });

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