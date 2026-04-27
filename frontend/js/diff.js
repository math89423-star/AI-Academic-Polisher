// 优化的文本差异对比库 - 按句子/短语块进行对比
// 适用于 AI 润色场景，避免过度标记微小差异

class TextDiff {
    constructor() {
        this.INSERT = 1;
        this.DELETE = -1;
        this.EQUAL = 0;
    }

    // 将文本分割为句子块（中英文兼容）
    splitIntoSentences(text) {
        // 中文句子结束符：。！？；
        // 英文句子结束符：. ! ? ;
        // 同时保留换行符作为分隔
        const sentences = [];
        const regex = /[^。！？；.!?;\n]+[。！？；.!?;\n]*/g;
        let match;

        while ((match = regex.exec(text)) !== null) {
            const sentence = match[0];
            if (sentence.trim()) {
                sentences.push(sentence);
            }
        }

        // 处理末尾没有标点的情况
        const lastIndex = sentences.join('').length;
        if (lastIndex < text.length) {
            const remaining = text.substring(lastIndex);
            if (remaining.trim()) {
                sentences.push(remaining);
            }
        }

        return sentences;
    }

    // 计算两个句子的相似度（基于字符重叠率）
    similarity(s1, s2) {
        if (s1 === s2) return 1.0;
        if (!s1 || !s2) return 0.0;

        const len1 = s1.length;
        const len2 = s2.length;
        const maxLen = Math.max(len1, len2);

        // 使用编辑距离计算相似度
        const distance = this.levenshteinDistance(s1, s2);
        return 1 - (distance / maxLen);
    }

    // 计算编辑距离
    levenshteinDistance(s1, s2) {
        const len1 = s1.length;
        const len2 = s2.length;
        const dp = Array(len1 + 1).fill(null).map(() => Array(len2 + 1).fill(0));

        for (let i = 0; i <= len1; i++) dp[i][0] = i;
        for (let j = 0; j <= len2; j++) dp[0][j] = j;

        for (let i = 1; i <= len1; i++) {
            for (let j = 1; j <= len2; j++) {
                if (s1[i - 1] === s2[j - 1]) {
                    dp[i][j] = dp[i - 1][j - 1];
                } else {
                    dp[i][j] = Math.min(
                        dp[i - 1][j] + 1,    // 删除
                        dp[i][j - 1] + 1,    // 插入
                        dp[i - 1][j - 1] + 1 // 替换
                    );
                }
            }
        }

        return dp[len1][len2];
    }

    // 主差异计算方法
    diff(text1, text2) {
        // 快速路径：完全相同
        if (text1 === text2) {
            return text1 ? [[this.EQUAL, text1]] : [];
        }

        // 快速路径：一个为空
        if (!text1) return [[this.INSERT, text2]];
        if (!text2) return [[this.DELETE, text1]];

        // 按句子分割
        const sentences1 = this.splitIntoSentences(text1);
        const sentences2 = this.splitIntoSentences(text2);

        // 使用动态规划进行句子级别的对比
        return this.sentenceDiff(sentences1, sentences2);
    }

    // 句子级别的差异对比
    sentenceDiff(sentences1, sentences2) {
        const len1 = sentences1.length;
        const len2 = sentences2.length;
        const diffs = [];

        // 相似度阈值：超过此值认为是同一句子（只是微调）
        // 降AI率系统需要更严格的标注，降低阈值到0.3
        const SIMILARITY_THRESHOLD = 0.3;

        // 动态规划矩阵
        const dp = Array(len1 + 1).fill(null).map(() => Array(len2 + 1).fill(0));
        const path = Array(len1 + 1).fill(null).map(() => Array(len2 + 1).fill(null));

        // 初始化
        for (let i = 0; i <= len1; i++) {
            dp[i][0] = i;
            if (i > 0) path[i][0] = 'delete';
        }
        for (let j = 0; j <= len2; j++) {
            dp[0][j] = j;
            if (j > 0) path[0][j] = 'insert';
        }

        // 填充 DP 表
        for (let i = 1; i <= len1; i++) {
            for (let j = 1; j <= len2; j++) {
                const sim = this.similarity(sentences1[i - 1], sentences2[j - 1]);

                if (sim >= SIMILARITY_THRESHOLD) {
                    // 相似度高但不完全相同，进行字符级对比
                    if (sim === 1.0) {
                        // 完全相同
                        dp[i][j] = dp[i - 1][j - 1];
                        path[i][j] = 'match';
                    } else {
                        // 相似但有差异，标记为需要字符级对比
                        dp[i][j] = dp[i - 1][j - 1];
                        path[i][j] = 'char_diff';
                    }
                } else {
                    // 选择代价最小的操作
                    const deleteCost = dp[i - 1][j] + 1;
                    const insertCost = dp[i][j - 1] + 1;
                    const replaceCost = dp[i - 1][j - 1] + 2;

                    if (deleteCost <= insertCost && deleteCost <= replaceCost) {
                        dp[i][j] = deleteCost;
                        path[i][j] = 'delete';
                    } else if (insertCost <= replaceCost) {
                        dp[i][j] = insertCost;
                        path[i][j] = 'insert';
                    } else {
                        dp[i][j] = replaceCost;
                        path[i][j] = 'replace';
                    }
                }
            }
        }

        // 回溯路径生成差异
        let i = len1, j = len2;
        const operations = [];

        while (i > 0 || j > 0) {
            const op = path[i][j];

            if (op === 'match') {
                operations.unshift({ type: this.EQUAL, text: sentences2[j - 1] });
                i--; j--;
            } else if (op === 'char_diff') {
                // 进行字符级精细对比
                const charDiffs = this.characterDiff(sentences1[i - 1], sentences2[j - 1]);
                // 反向遍历，避免 unshift 导致顺序反转
                for (let k = charDiffs.length - 1; k >= 0; k--) {
                    operations.unshift(charDiffs[k]);
                }
                i--; j--;
            } else if (op === 'delete') {
                operations.unshift({ type: this.DELETE, text: sentences1[i - 1] });
                i--;
            } else if (op === 'insert') {
                operations.unshift({ type: this.INSERT, text: sentences2[j - 1] });
                j--;
            } else if (op === 'replace') {
                // 替换操作：进行字符级对比而不是简单的删除+插入
                const charDiffs = this.characterDiff(sentences1[i - 1], sentences2[j - 1]);
                // 反向遍历，避免 unshift 导致顺序反转
                for (let k = charDiffs.length - 1; k >= 0; k--) {
                    operations.unshift(charDiffs[k]);
                }
                i--; j--;
            }
        }

        // 合并连续的相同类型操作
        for (let k = 0; k < operations.length; k++) {
            const op = operations[k];
            diffs.push([op.type, op.text]);
        }

        return this.mergeDiffs(diffs);
    }

    // 字符级精细对比（用于相似句子）
    characterDiff(text1, text2) {
        const len1 = text1.length;
        const len2 = text2.length;
        const dp = Array(len1 + 1).fill(null).map(() => Array(len2 + 1).fill(0));
        const path = Array(len1 + 1).fill(null).map(() => Array(len2 + 1).fill(null));

        for (let i = 0; i <= len1; i++) {
            dp[i][0] = i;
            if (i > 0) path[i][0] = 'delete';
        }
        for (let j = 0; j <= len2; j++) {
            dp[0][j] = j;
            if (j > 0) path[0][j] = 'insert';
        }

        for (let i = 1; i <= len1; i++) {
            for (let j = 1; j <= len2; j++) {
                if (text1[i - 1] === text2[j - 1]) {
                    dp[i][j] = dp[i - 1][j - 1];
                    path[i][j] = 'match';
                } else {
                    const deleteCost = dp[i - 1][j] + 1;
                    const insertCost = dp[i][j - 1] + 1;
                    const replaceCost = dp[i - 1][j - 1] + 1;

                    if (deleteCost <= insertCost && deleteCost <= replaceCost) {
                        dp[i][j] = deleteCost;
                        path[i][j] = 'delete';
                    } else if (insertCost <= replaceCost) {
                        dp[i][j] = insertCost;
                        path[i][j] = 'insert';
                    } else {
                        dp[i][j] = replaceCost;
                        path[i][j] = 'replace';
                    }
                }
            }
        }

        // 回溯生成字符级差异
        let i = len1, j = len2;
        const operations = [];

        while (i > 0 || j > 0) {
            const op = path[i][j];

            if (op === 'match') {
                operations.unshift({ type: this.EQUAL, text: text2[j - 1] });
                i--; j--;
            } else if (op === 'delete') {
                operations.unshift({ type: this.DELETE, text: text1[i - 1] });
                i--;
            } else if (op === 'insert') {
                operations.unshift({ type: this.INSERT, text: text2[j - 1] });
                j--;
            } else if (op === 'replace') {
                // 先插入 INSERT，再插入 DELETE，这样 unshift 后顺序才正确
                operations.unshift({ type: this.INSERT, text: text2[j - 1] });
                operations.unshift({ type: this.DELETE, text: text1[i - 1] });
                i--; j--;
            }
        }

        return operations;
    }

    // 合并连续的相同类型差异
    mergeDiffs(diffs) {
        if (diffs.length === 0) return diffs;

        const merged = [];
        let current = diffs[0];

        for (let i = 1; i < diffs.length; i++) {
            if (diffs[i][0] === current[0]) {
                // 相同类型，合并
                current = [current[0], current[1] + diffs[i][1]];
            } else {
                merged.push(current);
                current = diffs[i];
            }
        }
        merged.push(current);

        return merged;
    }

    // 将差异转换为 HTML（带高亮）
    // text1 是原文，text2 是润色文本
    // DELETE 表示原文中被删除的内容（红色删除线）
    // INSERT 表示润色文本中新增的内容（绿色高亮）
    diffToHtml(diffs) {
        const html = [];
        for (let i = 0; i < diffs.length; i++) {
            const op = diffs[i][0];
            const text = diffs[i][1];
            const escapedText = this.escapeHtml(text);

            switch (op) {
                case this.DELETE:
                    // 原文中的内容被删除 - 显示为红色删除线
                    html.push('<span class="diff-delete">' + escapedText + '</span>');
                    break;
                case this.INSERT:
                    // 润色文本中新增的内容 - 显示为绿色高亮
                    html.push('<span class="diff-insert">' + escapedText + '</span>');
                    break;
                case this.EQUAL:
                    html.push('<span>' + escapedText + '</span>');
                    break;
            }
        }
        return html.join('');
    }

    // HTML 转义
    escapeHtml(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;')
            .replace(/\n/g, '<br>');
    }

    // 提取纯文本（去除所有 HTML 标签）
    extractPlainText(html) {
        const temp = document.createElement('div');
        temp.innerHTML = html;
        return temp.textContent || temp.innerText || '';
    }
}

// 导出为全局变量
window.TextDiff = TextDiff;
