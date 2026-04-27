document.addEventListener('DOMContentLoaded', () => {
    const USER_KEY = 'user_username';
    let currentUsername = localStorage.getItem(USER_KEY);

    let taskCache = {};
    let currentViewingId = null;
    let isDiffMode = false; // 对比模式标志
    let originalTextCache = ''; // 缓存原始文本用于对比

    const loginContainer = document.getElementById('login-container');
    const workContainer = document.getElementById('work-container');
    const originalText = document.getElementById('original-text');
    const polishedText = document.getElementById('polished-text');
    const statusBox = document.getElementById('status-box');
    const serverMsg = document.getElementById('server-msg');

    const docxInfoBox = document.getElementById('docx-info-box');
    const docxFilename = document.getElementById('docx-filename');

    const polishBtn = document.getElementById('polish-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    const resumeBtn = document.getElementById('resume-btn');
    const uploadDocxBtn = document.getElementById('upload-docx-btn');
    const docxFileInput = document.getElementById('docx-file-input');
    const downloadResultBtn = document.getElementById('download-result-btn');
    const diffToggleBtn = document.getElementById('diff-toggle-btn');
    const copyResultBtn = document.getElementById('copy-result-btn');

    // 初始化 TextDiff 实例
    const textDiff = new TextDiff();

    // 错误提示函数
    function showErrorToast(errorType, errorMessage, suggestion) {
        const toast = document.createElement('div');
        toast.className = 'error-toast';
        toast.innerHTML = `
            <div class="error-toast-title">错误类型: ${errorType}</div>
            <div class="error-toast-message">${errorMessage}</div>
            ${suggestion ? `<div class="error-toast-message" style="margin-top: 8px; font-weight: 500;">💡 ${suggestion}</div>` : ''}
        `;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }


    // 🟢 策略动态加载逻辑
    const strategyContainer = document.getElementById('strategy-container');
    async function loadStrategies() {
        try {
            const res = await fetch('/api/tasks/strategies');
            if (!res.ok) throw new Error("获取策略失败");
            const strategies = await res.json();
            
            strategyContainer.innerHTML = ''; 
            
            strategies.forEach((st, index) => {
                const label = document.createElement('label');
                label.style.marginRight = '15px';
                label.style.cursor = 'pointer';
                if (st.color) label.style.color = st.color;
                
                const input = document.createElement('input');
                input.type = 'radio';
                input.name = 'strategy';
                input.value = st.id;
                // 默认选中第一个
                if (index === 0) input.checked = true;
                
                label.appendChild(input);
                label.appendChild(document.createTextNode(' ' + st.name));
                strategyContainer.appendChild(label);
            });
        } catch (err) {
            strategyContainer.innerHTML = '<span style="color: red;">策略库加载失败，请刷新重试</span>';
        }
    }

    if (currentUsername) {
        showWorkContainer();
        loadHistory();
        loadStrategies(); // 初始化加载策略库
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
                loadStrategies(); // 初始化加载策略库
            } else {
                const data = await res.json();
                loginMsg.innerText = data.error || "验证失败"; 
            }
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
                    task_type: t.task_type || 'text', 
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

            const typeIcon = t.task_type === 'docx' ? '📄' : '📝';
            const preview = t.task_type === 'docx' ? t.title : (t.original ? t.original.substring(0, 10) + '...' : '新任务');

            div.innerHTML = `<div class="history-time"><span>${t.time}</span> <span>${statusIcon}</span></div><div class="history-preview">${typeIcon} ${preview}</div>`;
            div.onclick = () => switchTask(id);
            listElem.appendChild(div);
        });
    }

    function switchTask(id) {
        currentViewingId = id;

        if (!id) {
            originalText.classList.remove('hidden');
            docxInfoBox.classList.add('hidden');
            originalText.value = '';
            polishedText.textContent = '润色结果将在这里流式输出...';
            polishedText.classList.remove('diff-mode');
            statusBox.innerText = '待命'; serverMsg.innerText = '';

            polishBtn.classList.remove('hidden');
            uploadDocxBtn.classList.remove('hidden');

            cancelBtn.classList.add('hidden');
            resumeBtn.classList.add('hidden');
            downloadResultBtn.classList.add('hidden');
            diffToggleBtn.classList.add('hidden');
            copyResultBtn.classList.add('hidden');
            isDiffMode = false;
            diffToggleBtn.classList.remove('active');
            renderHistoryList();
            return;
        }

        const t = taskCache[id];

        if (t.task_type === 'docx') {
            originalText.classList.add('hidden');
            docxInfoBox.classList.remove('hidden');
            docxInfoBox.style.display = 'flex';
            docxFilename.innerText = t.title || "Word文档";

            polishBtn.classList.add('hidden');
            uploadDocxBtn.classList.add('hidden');
            diffToggleBtn.classList.add('hidden'); // Word 文档不支持对比模式
            originalTextCache = '';
        } else {
            originalText.classList.remove('hidden');
            docxInfoBox.classList.add('hidden');
            originalText.value = t.original;
            originalTextCache = t.original; // 缓存原始文本

            polishBtn.classList.add('hidden');
            uploadDocxBtn.classList.add('hidden');

            // 如果有润色结果，显示对比按钮
            if (t.polished && t.polished.trim()) {
                diffToggleBtn.classList.remove('hidden');
                copyResultBtn.classList.remove('hidden');
            } else {
                diffToggleBtn.classList.add('hidden');
                copyResultBtn.classList.add('hidden');
            }
        }

        // 显示润色结果（纯文本或对比模式）
        if (isDiffMode && t.task_type !== 'docx' && t.polished) {
            showDiffMode(originalTextCache, t.polished);
        } else {
            polishedText.textContent = t.polished || "";
            polishedText.classList.remove('diff-mode');
        }

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

    // 🟢 纯文本提交时追加策略参数
    polishBtn.onclick = async () => {
        const text = originalText.value.trim();
        const modeInput = document.querySelector('input[name="mode"]:checked');
        const mode = modeInput ? modeInput.value : 'zh';

        // 获取动态渲染出的选中策略
        const strategyInput = document.querySelector('input[name="strategy"]:checked');
        const strategy = strategyInput ? strategyInput.value : 'standard';

        if (!text) return;

        // 检查文本是否重复
        try {
            const dupRes = await fetch('/api/tasks/check_duplicate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: currentUsername, text: text })
            });

            if (dupRes.ok) {
                const dupData = await dupRes.json();
                if (dupData.is_duplicate) {
                    // 弹出确认对话框
                    const userConfirm = confirm(
                        `检测到该文本在近期（24小时内）已优化过。\n` +
                        `上次处理时间: ${new Date(dupData.last_processed).toLocaleString()}\n\n` +
                        `是否仍要进行新一轮润色？`
                    );
                    if (!userConfirm) {
                        return; // 用户取消
                    }
                }
            }
        } catch (err) {
            console.warn('重复检测失败，继续执行:', err);
        }

        polishBtn.disabled = true;

        try {
            const res = await fetch('/api/tasks/create', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: currentUsername, text: text, mode: mode, strategy: strategy })
            });
            const data = await res.json();
            if (res.ok) {
                taskCache[data.task_id] = {
                    id: data.task_id, time: getFormattedTime(), original: text, title: "文本片段",
                    polished: "", status: 'queued', serverInfo: '正在排队...', downloadUrl: '', task_type: 'text'
                };
                switchTask(data.task_id);
                startStreaming(data.task_id);
            } else {
                alert(data.error || "创建任务失败");
            }
        } catch (err) {
            alert("网络错误，请稍后重试");
        } finally {
            polishBtn.disabled = false;
        }
    };

    // 🟢 Word 上传提交时追加策略参数
    if (uploadDocxBtn && docxFileInput) {
        uploadDocxBtn.onclick = () => docxFileInput.click();

        docxFileInput.onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const modeInput = document.querySelector('input[name="mode"]:checked');
            const mode = modeInput ? modeInput.value : 'zh';
            
            // 获取动态渲染出的选中策略
            const strategyInput = document.querySelector('input[name="strategy"]:checked');
            const strategy = strategyInput ? strategyInput.value : 'standard';

            const formData = new FormData();
            formData.append('file', file);
            formData.append('username', currentUsername);
            formData.append('mode', mode);
            formData.append('strategy', strategy); // 追加策略参数到表单

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
                        task_type: 'docx' 
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
                    // 流式输出时始终显示纯文本，实时追加
                    polishedText.textContent = t.polished;
                    polishedText.classList.remove('diff-mode');
                    // 自动滚动到底部
                    polishedText.scrollTop = polishedText.scrollHeight;

                    // 显示复制和对比按钮（流式输出时也可以使用）
                    if (t.polished.trim()) {
                        copyResultBtn.classList.remove('hidden');
                        diffToggleBtn.classList.remove('hidden');
                    }
                }
            } else if (data.type === 'done') {
                t.status = 'completed'; t.serverInfo = '';
                if (currentViewingId == taskId) {
                    switchTask(taskId);
                } else {
                    renderHistoryList();
                    if (currentViewingId === null) {
                        polishBtn.disabled = false;
                        uploadDocxBtn.disabled = false;
                    }
                }
                source.close();
            } else if (data.type === 'fatal') {
                t.status = 'failed'; t.serverInfo = '异常中断，可重试';

                // 解析错误类型并显示详细提示
                const errorContent = data.content || '未知错误';
                let errorType = '系统错误';
                let suggestion = '请稍后重试或联系管理员';

                if (errorContent.includes('timeout') || errorContent.includes('超时')) {
                    errorType = '网络超时';
                    suggestion = '请检查网络连接或稍后重试';
                } else if (errorContent.includes('API') || errorContent.includes('api_key')) {
                    errorType = 'API 配置错误';
                    suggestion = '请检查 API Key 是否正确配置';
                } else if (errorContent.includes('quota') || errorContent.includes('欠费')) {
                    errorType = 'API 额度不足';
                    suggestion = '请充值 API 账户或更换 API Key';
                } else if (errorContent.includes('content') || errorContent.includes('安全')) {
                    errorType = '内容安全拦截';
                    suggestion = '文本可能包含敏感内容，请修改后重试';
                }

                if (currentViewingId == taskId) {
                    showErrorToast(errorType, errorContent, suggestion);
                    switchTask(taskId);
                } else {
                    renderHistoryList();
                    if (currentViewingId === null) {
                        polishBtn.disabled = false;
                        uploadDocxBtn.disabled = false;
                    }
                }
                source.close();
            }
        };

        source.onerror = () => {
            const t = taskCache[taskId];
            if (t && (t.status === 'processing' || t.status === 'queued')) {
                t.status = 'failed';
                t.serverInfo = '网络断开，进度已保存';
                if (t.sseSource) { t.sseSource.close(); t.sseSource = null; }
                if (currentViewingId == taskId) {
                    showErrorToast('网络错误', '与服务器的连接已断开', '请检查网络连接或刷新页面重试');
                    switchTask(taskId);
                } else {
                    renderHistoryList();
                }
            } else { source.close(); }
        };
    }

    document.getElementById('logout-btn').addEventListener('click', () => {
        localStorage.removeItem(USER_KEY); location.reload();
    });

    // 对比模式切换
    diffToggleBtn.addEventListener('click', () => {
        if (!currentViewingId) return;
        const t = taskCache[currentViewingId];
        if (!t || !t.polished || t.task_type === 'docx') return;

        isDiffMode = !isDiffMode;
        if (isDiffMode) {
            diffToggleBtn.classList.add('active');
            diffToggleBtn.textContent = '📝 纯文本';
            showDiffMode(originalTextCache, t.polished);
        } else {
            diffToggleBtn.classList.remove('active');
            diffToggleBtn.textContent = '📊 对比模式';
            polishedText.textContent = t.polished;
            polishedText.classList.remove('diff-mode');
        }
    });

    // 显示对比模式
    function showDiffMode(original, polished) {
        const diffs = textDiff.diff(original, polished);
        const diffHtml = textDiff.diffToHtml(diffs);
        polishedText.innerHTML = diffHtml;
        polishedText.classList.add('diff-mode');
    }

    // 复制按钮 - 确保只复制纯文本
    copyResultBtn.addEventListener('click', () => {
        if (!currentViewingId) return;
        const t = taskCache[currentViewingId];
        if (!t || !t.polished) return;

        // 始终复制纯文本，无论当前是否在对比模式
        const plainText = t.polished;

        // 使用 Clipboard API
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(plainText).then(() => {
                const originalText = copyResultBtn.textContent;
                copyResultBtn.textContent = '✅ 已复制';
                setTimeout(() => {
                    copyResultBtn.textContent = originalText;
                }, 2000);
            }).catch(err => {
                console.error('复制失败:', err);
                fallbackCopy(plainText);
            });
        } else {
            fallbackCopy(plainText);
        }
    });

    // 降级复制方案
    function fallbackCopy(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            const originalText = copyResultBtn.textContent;
            copyResultBtn.textContent = '✅ 已复制';
            setTimeout(() => {
                copyResultBtn.textContent = originalText;
            }, 2000);
        } catch (err) {
            alert('复制失败，请手动复制');
        }
        document.body.removeChild(textarea);
    }
});