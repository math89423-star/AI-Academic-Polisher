document.addEventListener('DOMContentLoaded', () => {
    const USER_KEY = 'user_username';
    let currentUsername = localStorage.getItem(USER_KEY);
    
    let taskCache = {}; 
    let currentViewingId = null;

    const loginContainer = document.getElementById('login-container');
    const workContainer = document.getElementById('work-container');
    const originalText = document.getElementById('original-text');
    const polishedText = document.getElementById('polished-text');
    const statusBox = document.getElementById('status-box');
    const serverMsg = document.getElementById('server-msg');
    
    // 🟢 新增：Word 面板元素
    const docxInfoBox = document.getElementById('docx-info-box');
    const docxFilename = document.getElementById('docx-filename');
    
    const polishBtn = document.getElementById('polish-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    const resumeBtn = document.getElementById('resume-btn');
    const uploadDocxBtn = document.getElementById('upload-docx-btn');
    const docxFileInput = document.getElementById('docx-file-input');
    const downloadResultBtn = document.getElementById('download-result-btn');

    if (currentUsername) {
        showWorkContainer();
        loadHistory();
    }

    document.getElementById('login-btn').addEventListener('click', async () => {
        const username = document.getElementById('username-input').value.trim();
        const loginMsg = document.getElementById('login-msg');
        if (!username) return loginMsg.innerText = "用户名不能为空";

        try {
            const res = await fetch('/api/auth/login/user', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username })
            });
            if (res.ok) {
                localStorage.setItem(USER_KEY, username);
                currentUsername = username;
                showWorkContainer();
                loadHistory(); 
            } else { loginMsg.innerText = "验证失败"; }
        } catch (err) { loginMsg.innerText = '无法连接服务器'; }
    });

    function showWorkContainer() {
        loginContainer.classList.add('hidden');
        workContainer.classList.remove('hidden');
        document.getElementById('display-username').innerText = currentUsername;
    }

    async function loadHistory() {
        try {
            const res = await fetch(`/api/tasks/history?username=${currentUsername}`);
            if (!res.ok) return;
            const data = await res.json();
            
            taskCache = {};
            data.forEach(t => {
                taskCache[t.id] = {
                    id: t.id, time: t.created_at, original: t.original_text,
                    polished: t.polished_text, status: t.status, serverInfo: '',
                    task_type: t.task_type || 'text', // 🟢 记录类型
                    downloadUrl: t.download_url || '',
                    title: t.title
                };
            });
            renderHistoryList();
            if (data.length > 0 && !currentViewingId) switchTask(data[0].id);
        } catch (err) {}
    }

    function renderHistoryList() {
        const listElem = document.getElementById('history-list');
        listElem.innerHTML = '';
        Object.keys(taskCache).sort((a, b) => b - a).forEach(id => {
            const t = taskCache[id];
            const div = document.createElement('div');
            div.className = `history-item ${id == currentViewingId ? 'active' : ''}`;

            let statusIcon = '⏳';
            if(['completed', 'done'].includes(t.status)) statusIcon = '✅';
            if(['failed', 'cancelled'].includes(t.status)) statusIcon = '❌';

            // 列表图标区分
            const typeIcon = t.task_type === 'docx' ? '📄' : '📝';
            const preview = t.task_type === 'docx' ? t.title : (t.original.substring(0, 10) + '...');

            div.innerHTML = `<div class="history-time"><span>${t.time}</span> <span>${statusIcon}</span></div><div class="history-preview">${typeIcon} ${preview}</div>`;
            div.onclick = () => switchTask(id);
            listElem.appendChild(div);
        });
    }

    // 🟢 核心修复：根据 task_type 智能切换 UI 面板
    function switchTask(id) {
        currentViewingId = id;
        
        if (!id) {
            // 新建任务模式：显示文本框，显示所有上传按钮
            originalText.classList.remove('hidden');
            docxInfoBox.classList.add('hidden');
            originalText.value = ''; polishedText.value = '';
            statusBox.innerText = '待命'; serverMsg.innerText = '';
            
            polishBtn.classList.remove('hidden');
            uploadDocxBtn.classList.remove('hidden');
            cancelBtn.classList.add('hidden');
            resumeBtn.classList.add('hidden');
            downloadResultBtn.classList.add('hidden');
            renderHistoryList();
            return;
        }

        const t = taskCache[id];
        
        // 🟢 面板物理隔离逻辑
        if (t.task_type === 'docx') {
            originalText.classList.add('hidden');
            docxInfoBox.classList.remove('hidden');
            docxInfoBox.style.display = 'flex'; // 强制 flex 布局生效
            docxFilename.innerText = t.title || "Word文档";
            
            polishBtn.classList.add('hidden'); // 绝不让用户在 Word 模式点纯文本提交
            uploadDocxBtn.classList.add('hidden');
        } else {
            originalText.classList.remove('hidden');
            docxInfoBox.classList.add('hidden');
            originalText.value = t.original;
            
            polishBtn.classList.add('hidden'); 
            uploadDocxBtn.classList.add('hidden');
        }

        polishedText.value = t.polished || "";
        statusBox.innerText = ['completed', 'done'].includes(t.status) ? '✅ 润色完成' : (['failed', 'cancelled'].includes(t.status) ? '❌ 失败/中止' : '⏳ 处理中');
        serverMsg.innerText = t.serverInfo || '';
        
        if (t.downloadUrl) {
            downloadResultBtn.href = t.downloadUrl;
            downloadResultBtn.classList.remove('hidden');
        } else {
            downloadResultBtn.classList.add('hidden');
        }
        
        if (t.status === 'processing' || t.status === 'queued') {
            cancelBtn.classList.remove('hidden');
            resumeBtn.classList.add('hidden');
        } else if (t.status === 'cancelled' || t.status === 'failed') {
            cancelBtn.classList.add('hidden');
            resumeBtn.classList.remove('hidden'); 
        } else {
            cancelBtn.classList.add('hidden');
            resumeBtn.classList.add('hidden');
        }
        
        renderHistoryList();
    }

    document.getElementById('new-task-btn').onclick = () => switchTask(null);

    function getFormattedTime() {
        const now = new Date();
        const y = now.getFullYear(), m = String(now.getMonth()+1).padStart(2,'0'), d = String(now.getDate()).padStart(2,'0');
        const h = String(now.getHours()).padStart(2,'0'), min = String(now.getMinutes()).padStart(2,'0'), s = String(now.getSeconds()).padStart(2,'0');
        return `${y}-${m}-${d} ${h}:${min}:${s}`;
    }

    // 纯文本提交
    polishBtn.onclick = async () => {
        const text = originalText.value.trim();
        const mode = document.querySelector('input[name="mode"]:checked').value;
        if (!text) return;
        polishBtn.disabled = true;

        try {
            const res = await fetch('/api/tasks/create', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: currentUsername, text: text, mode: mode })
            });
            const data = await res.json();
            if (res.ok) {
                taskCache[data.task_id] = {
                    id: data.task_id, time: getFormattedTime(), original: text, title: "文本片段",
                    polished: "", status: 'queued', serverInfo: '正在排队...', downloadUrl: '', task_type: 'text'
                };
                switchTask(data.task_id);
                startStreaming(data.task_id);
                polishBtn.disabled = false; 
            }
        } catch (err) {}
    };

    // 🟢 Word 文档提交
    if (uploadDocxBtn && docxFileInput) {
        uploadDocxBtn.onclick = () => docxFileInput.click();

        docxFileInput.onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const mode = document.querySelector('input[name="mode"]:checked').value;
            const formData = new FormData();
            formData.append('file', file);
            formData.append('username', currentUsername);
            formData.append('mode', mode);

            uploadDocxBtn.disabled = true;
            uploadDocxBtn.innerText = "上传中...";

            try {
                const res = await fetch('/api/tasks/upload_docx', {
                    method: 'POST', body: formData 
                });
                const data = await res.json();
                
                if (res.ok) {
                    taskCache[data.task_id] = {
                        id: data.task_id, time: getFormattedTime(), original: "", title: file.name,
                        polished: "", status: 'queued', serverInfo: '正在排队解析文档...', downloadUrl: '',
                        task_type: 'docx' // 🟢 明确打上标记
                    };
                    switchTask(data.task_id);
                    startStreaming(data.task_id);
                } else { alert(data.error || "上传失败"); }
            } catch (err) { alert("网络或上传错误"); } 
            finally {
                uploadDocxBtn.innerText = "📄 上传 Word";
                uploadDocxBtn.disabled = false;
                docxFileInput.value = ""; 
            }
        };
    }

    cancelBtn.onclick = async () => {
        if (!currentViewingId) return;
        const t = taskCache[currentViewingId];
        if (!t) return;

        if (t.sseSource) { t.sseSource.close(); t.sseSource = null; }
        t.status = 'cancelled';
        t.serverInfo = '已手动终止，进度已保存';
        switchTask(currentViewingId); 

        try {
            await fetch(`/api/tasks/${currentViewingId}/cancel`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: currentUsername })
            });
        } catch (err) {}
    };

    resumeBtn.onclick = async () => {
        if (!currentViewingId) return;
        const t = taskCache[currentViewingId];
        resumeBtn.disabled = true;
        resumeBtn.innerText = "唤醒中...";

        try {
            const res = await fetch(`/api/tasks/${currentViewingId}/resume`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: currentUsername })
            });
            if (res.ok) {
                t.status = 'queued';
                t.serverInfo = '重新排队中...';
                switchTask(currentViewingId); 
                startStreaming(currentViewingId); 
            }
        } catch (err) {}
        finally {
            resumeBtn.innerText = "▶️ 继续执行";
            resumeBtn.disabled = false;
        }
    };

    function startStreaming(taskId) {
        const source = new EventSource(`/api/tasks/stream/${taskId}`);
        taskCache[taskId].sseSource = source; 

        source.onmessage = (e) => {
            const data = JSON.parse(e.data);
            const t = taskCache[taskId]; 

            if (data.type === 'block') {
                t.serverInfo = data.content.trim();
                if (currentViewingId == taskId) serverMsg.innerText = t.serverInfo;
            } else if (data.type === 'stream') {
                t.polished += data.content;
                if (currentViewingId == taskId) {
                    polishedText.value = t.polished;
                    polishedText.scrollTop = polishedText.scrollHeight;
                }
            } else if (data.type === 'download') {
                t.downloadUrl = data.content;
                if (currentViewingId == taskId) {
                    downloadResultBtn.href = t.downloadUrl;
                    downloadResultBtn.classList.remove('hidden');
                }
            } else if (data.type === 'done') {
                t.status = 'completed'; t.serverInfo = ''; 
                if (currentViewingId == taskId) switchTask(taskId); else renderHistoryList();
                source.close();
            } else if (data.type === 'fatal') {
                t.status = 'failed'; t.serverInfo = '异常中断，可重试';
                if (currentViewingId == taskId) switchTask(taskId); else renderHistoryList();
                source.close();
            }
        };

        source.onerror = () => {
            const t = taskCache[taskId];
            if (t && (t.status === 'processing' || t.status === 'queued')) {
                t.status = 'failed'; 
                t.serverInfo = '网络断开，进度已保存';
                if (t.sseSource) { t.sseSource.close(); t.sseSource = null; }
                if (currentViewingId == taskId) switchTask(taskId); else renderHistoryList();
            } else { source.close(); }
        };
    }

    document.getElementById('logout-btn').addEventListener('click', () => {
        localStorage.removeItem(USER_KEY); location.reload();
    });
});