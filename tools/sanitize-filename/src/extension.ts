import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

// ─── 全局状态 ───────────────────────────────────────────────
const processedFiles = new Set<string>();  // 已处理/已忽略的文件，避免重复弹窗
const pendingChecks = new Set<string>();   // 正在排队检测的文件，防止并发重复

/**
 * 获取扩展配置
 */
function getConfig(): vscode.WorkspaceConfiguration {
    return vscode.workspace.getConfiguration('sanitizeFilename');
}

/**
 * 将简单 glob 模式转换为正则表达式
 * 支持 **、*、? 三种通配符
 */
function globToRegex(pattern: string): RegExp {
    const escaped = pattern
        .replace(/[.+^${}()|[\]\\]/g, '\\$&')   // 先转义正则特殊字符
        .replace(/\\\*\\\*/g, '<<<DOUBLESTAR>>>') // 暂存 **
        .replace(/\\\*/g, '[^/\\\\]*')             // * → 匹配非路径分隔符
        .replace(/<<<DOUBLESTAR>>>/g, '.*')        // ** → 匹配任意
        .replace(/\\\?/g, '[^/\\\\]');             // ? → 匹配单个非路径分隔符
    return new RegExp(escaped);
}

/**
 * 检查路径是否在忽略列表中
 */
function isIgnored(filePath: string): boolean {
    const config = getConfig();
    const ignoredPatterns: string[] = config.get('ignoredPatterns') || [];

    return ignoredPatterns.some(pattern => globToRegex(pattern).test(filePath));
}

/**
 * 规范化文件名（核心逻辑）
 * @returns 规范化后的完整文件名（含扩展名）
 */
function sanitizeFilename(filename: string): string {
    const config = getConfig();
    // 注意：config.get('pattern') 的默认值来自 package.json，包含中文弯引号 “”‘’
    const patternStr: string = config.get('pattern') || '["\'(){}\\[\\]#&!@$%^*+=~`<>?|\\s“”‘’]';
    const replacement: string = config.get('replacement') || '_';
    const trimEdges: boolean = config.get('trimEdges') ?? true;
    const collapseConsecutive: boolean = config.get('collapseConsecutive') ?? true;
    const preserveExtension: boolean = config.get('preserveExtension') ?? true;

    let name = filename;
    let ext = '';

    // 分离扩展名
    if (preserveExtension) {
        const lastDot = filename.lastIndexOf('.');
        if (lastDot > 0) {
            ext = filename.slice(lastDot);
            name = filename.slice(0, lastDot);
        }
    }

    // 替换特殊字符
    let sanitized = name;
    try {
        const pattern = new RegExp(patternStr, 'g');
        sanitized = sanitized.replace(pattern, replacement);
        // 诊断日志
        const matched = name.match(pattern);
        if (matched && matched.length > 0) {
            console.log('[Sanitize Filename] Pattern matched in "' + filename + '": ' +
                matched.map(function(c) { return 'U+' + c.charCodeAt(0).toString(16).toUpperCase(); }).join(', '));
        }
    } catch (e) {
        console.error('[Sanitize Filename] Invalid regex pattern (' + patternStr.length + ' chars):', e);
        // 回退到安全的默认模式（包含中文弯引号）
        const defaultPattern = /["'(){}[\]#&!@$%^*+=~`<>?|\s“”‘’]/g;
        sanitized = sanitized.replace(defaultPattern, replacement);
    }

    // 合并连续的替换字符
    if (collapseConsecutive && replacement) {
        const escapedReplacement = replacement.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const consecutivePattern = new RegExp(escapedReplacement + '+', 'g');
        sanitized = sanitized.replace(consecutivePattern, replacement);
    }

    // 去除首尾的下划线、连字符、空格
    if (trimEdges) {
        sanitized = sanitized.replace(/^[\s_\-]+|[\s_\-]+$/g, '');
    }

    // 处理空文件名
    if (!sanitized) {
        sanitized = 'untitled';
    }

    return sanitized + ext;
}

/**
 * 检查文件名是否需要规范化
 */
function needsSanitization(filename: string): boolean {
    return sanitizeFilename(filename) !== filename;
}

/**
 * 重命名成功后，关闭旧文件标签页并打开新文件
 */
async function reopenAfterRename(oldPath: string, newPath: string): Promise<void> {
    const newUri = vscode.Uri.file(newPath);

    // 1. 关闭所有显示旧路径的标签页
    try {
        const tabsToClose: vscode.Tab[] = [];
        const tabGroups = (vscode.window as any).tabGroups;
        if (tabGroups && tabGroups.all) {
            for (const group of tabGroups.all) {
                for (const tab of group.tabs) {
                    const input = tab.input as { uri?: vscode.Uri } | undefined;
                    if (input && input.uri && input.uri.fsPath === oldPath) {
                        tabsToClose.push(tab);
                    }
                }
            }
            if (tabsToClose.length > 0) {
                await tabGroups.close(tabsToClose);
            }
        }
    } catch {
        // tabGroups API 不可用（VS Code < 1.87），静默降级
        console.warn('[Sanitize Filename] tabGroups API not available, skip closing old tabs');
    }

    // 2. 打开新文件
    try {
        const newDoc = await vscode.workspace.openTextDocument(newUri);
        await vscode.window.showTextDocument(newDoc);
    } catch {
        // 打不开时静默降级（至少重命名成功了）
    }
}

/**
 * 执行文件重命名
 * @returns true 表示重命名成功，false 表示被跳过或失败
 */
async function performRename(oldUri: vscode.Uri, newName: string): Promise<boolean> {
    const oldPath = oldUri.fsPath;
    const dir = path.dirname(oldPath);
    const newPath = path.join(dir, newName);

    // 文件名没变，跳过
    if (oldPath === newPath) {
        return false;
    }

    // 检查旧文件是否仍然存在（可能已被外部重命名）
    if (!fs.existsSync(oldPath)) {
        console.warn('[Sanitize Filename] File no longer exists: ' + oldPath);
        return false;
    }

    // 目标文件已存在
    if (fs.existsSync(newPath)) {
        const choice = await vscode.window.showWarningMessage(
            '目标文件 "' + newName + '" 已存在，是否覆盖？',
            { modal: true },
            '覆盖',
            '取消'
        );
        if (choice !== '覆盖') {
            return false;
        }
        // 先删除目标文件
        try {
            await fs.promises.unlink(newPath);
        } catch {
            vscode.window.showErrorMessage('无法删除已存在的目标文件 "' + newName + '"');
            return false;
        }
    }

    // 记录：重命名前文件是否在编辑器中打开
    const wasOpen = vscode.workspace.textDocuments.some(
        doc => doc.uri.fsPath === oldPath
    );

    try {
        await fs.promises.rename(oldPath, newPath);

        // 重命名成功后：如果文件之前已在编辑器中打开，关闭旧标签页并打开新文件
        if (wasOpen) {
            await reopenAfterRename(oldPath, newPath);
        }

        return true;
    } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        // 区分常见错误类型给出更友好的提示
        if (message.includes('EPERM') || message.includes('EACCES')) {
            vscode.window.showErrorMessage(
                '重命名失败: 权限不足，无法修改 "' + path.basename(oldPath) + '"。请关闭文件后再试。'
            );
        } else if (message.includes('EBUSY')) {
            vscode.window.showErrorMessage(
                '重命名失败: 文件 "' + path.basename(oldPath) + '" 正在被使用，请关闭后重试。'
            );
        } else {
            vscode.window.showErrorMessage(
                '重命名失败: ' + message
            );
        }
        return false;
    }
}

/**
 * 处理单个文件的规范化检测
 */
async function handleFile(
    fileUri: vscode.Uri,
    context: 'open' | 'save' | 'create' | 'manual' = 'manual'
): Promise<void> {
    // 仅处理 file:// 协议
    if (fileUri.scheme !== 'file') {
        return;
    }

    const filePath = fileUri.fsPath;
    const filename = path.basename(filePath);

    // 正在排队检测 → 防止并发重复
    if (pendingChecks.has(filePath)) {
        return;
    }
    // 已处理过的文件不再重复打扰（手动触发和保存场景除外：用户主动操作应每次都执行）
    if ((context === 'open' || context === 'create') && processedFiles.has(filePath)) {
        return;
    }

    // 忽略列表
    if (isIgnored(filePath)) {
        return;
    }

    // 文件名无需规范化
    if (!needsSanitization(filename)) {
        console.log('[Sanitize Filename] "' + filename + '" — no special chars detected, skipping (context: ' + context + ')');
        // 手动触发时给个反馈
        if (context === 'manual') {
            vscode.window.showInformationMessage('文件名 "' + filename + '" 已经是规范格式，无需处理。');
        }
        return;
    }

    console.log('[Sanitize Filename] "' + filename + '" — special chars DETECTED, prompting user (context: ' + context + ')');

    // 标记为处理中
    pendingChecks.add(filePath);

    try {
        const newName = sanitizeFilename(filename);
        const config = getConfig();
        const mode: string = config.get('mode') || 'prompt';

        switch (mode) {
            case 'auto': {
                const success = await performRename(fileUri, newName);
                if (success) {
                    vscode.window.showInformationMessage(
                        '文件名已自动规范化: "' + filename + '" → "' + newName + '"'
                    );
                    processedFiles.delete(filePath);
                }
                break;
            }

            case 'warn': {
                // 仅显示警告，不主动重命名
                vscode.window.showWarningMessage(
                    '文件名 "' + filename + '" 包含特殊字符，建议规范化为 "' + newName + '"',
                    '立即规范化',
                    '忽略'
                ).then(async (choice) => {
                    if (choice === '立即规范化') {
                        const success = await performRename(fileUri, newName);
                        if (success) {
                            processedFiles.delete(filePath);
                        }
                    } else {
                        processedFiles.add(filePath);
                    }
                });
                break;
            }

            case 'prompt':
            default: {
                const choice = await vscode.window.showInformationMessage(
                    '检测到文件名包含特殊字符\n\n当前: "' + filename + '"\n建议: "' + newName + '"',
                    { modal: false },
                    '是，重命名',
                    '否，保留原样',
                    '始终自动处理'
                );

                if (choice === '是，重命名') {
                    const success = await performRename(fileUri, newName);
                    if (success) {
                        processedFiles.delete(filePath);
                    }
                } else if (choice === '始终自动处理') {
                    await config.update('mode', 'auto', vscode.ConfigurationTarget.Global);
                    vscode.window.showInformationMessage('已切换为自动模式，后续将自动规范化文件名。');
                    const success = await performRename(fileUri, newName);
                    if (success) {
                        processedFiles.delete(filePath);
                    }
                } else {
                    // 用户选择保留原样
                    processedFiles.add(filePath);
                }
                break;
            }
        }
    } finally {
        pendingChecks.delete(filePath);
    }
}

/**
 * 递归扫描工作区中需要规范化的文件
 */
async function scanProblematicFiles(): Promise<vscode.Uri[]> {
    if (!vscode.workspace.workspaceFolders) {
        return [];
    }

    const config = getConfig();
    const ignoredPatterns: string[] = config.get('ignoredPatterns') || [];
    // 构建 findFiles 的排除模式（追加到默认排除）
    const excludePattern = '{' + ignoredPatterns.join(',') + '}';

    const allFiles: vscode.Uri[] = [];
    for (const folder of vscode.workspace.workspaceFolders) {
        const uris = await vscode.workspace.findFiles(
            new vscode.RelativePattern(folder, '**/*'),
            '{**/node_modules/**,**/.git/**,' + excludePattern + '}'
        );
        allFiles.push(...uris);
    }

    // 就地过滤，避免额外数组分配
    return allFiles.filter(f => {
        const filename = path.basename(f.fsPath);
        return needsSanitization(filename) && !isIgnored(f.fsPath);
    });
}

// ─── 激活扩展 ───────────────────────────────────────────────

export function activate(context: vscode.ExtensionContext) {
    console.log('[Sanitize Filename] Extension activated');

    const config = getConfig();

    // ── 命令：规范化当前文件 ──────────────────────────────
    const sanitizeCurrentCmd = vscode.commands.registerCommand(
        'sanitizeFilename.sanitizeCurrent',
        async (uri?: vscode.Uri) => {
            const targetUri = uri || vscode.window.activeTextEditor?.document.uri;
            if (!targetUri) {
                vscode.window.showWarningMessage('没有选中的文件');
                return;
            }
            await handleFile(targetUri, 'manual');
        }
    );

    // ── 命令：扫描并规范化工作区全部文件 ─────────────────
    const sanitizeAllCmd = vscode.commands.registerCommand(
        'sanitizeFilename.sanitizeAllInWorkspace',
        async () => {
            const problematicFiles = await scanProblematicFiles();

            if (problematicFiles.length === 0) {
                vscode.window.showInformationMessage('工作区中没有需要规范化的文件名。');
                return;
            }

            const choice = await vscode.window.showWarningMessage(
                '发现 ' + problematicFiles.length + ' 个文件名包含特殊字符，是否全部规范化？',
                '全部规范化',
                '查看列表',
                '取消'
            );

            if (choice === '全部规范化') {
                let successCount = 0;
                let failCount = 0;

                await vscode.window.withProgress({
                    location: vscode.ProgressLocation.Notification,
                    title: '正在规范化文件名...',
                    cancellable: true
                }, async (progress, token) => {
                    const total = problematicFiles.length;
                    for (let i = 0; i < total; i++) {
                        if (token.isCancellationRequested) {
                            break;
                        }

                        const file = problematicFiles[i];
                        const fname = path.basename(file.fsPath);
                        const newName = sanitizeFilename(fname);

                        progress.report({
                            increment: 100 / total,
                            message: (i + 1) + '/' + total + ': ' + fname
                        });

                        const success = await performRename(file, newName);
                        if (success) {
                            successCount++;
                        } else {
                            failCount++;
                        }
                    }
                });

                vscode.window.showInformationMessage(
                    '规范化完成: ' + successCount + ' 个成功, ' + failCount + ' 个失败'
                );
            } else if (choice === '查看列表') {
                const items = problematicFiles.map(f => ({
                    label: path.basename(f.fsPath),
                    description: sanitizeFilename(path.basename(f.fsPath)),
                    detail: f.fsPath
                }));

                const selected = await vscode.window.showQuickPick(items, {
                    placeHolder: '选择要规范化的文件（可多选）',
                    canPickMany: true
                });

                if (selected && selected.length > 0) {
                    for (const item of selected) {
                        const uri = vscode.Uri.file(item.detail);
                        await handleFile(uri, 'manual');
                    }
                }
            }
        }
    );

    // ── 命令：切换自动模式 ──────────────────────────────
    const toggleAutoCmd = vscode.commands.registerCommand(
        'sanitizeFilename.toggleAutoMode',
        async () => {
            const cfg = getConfig();
            const currentMode: string = cfg.get('mode') || 'prompt';
            const newMode = currentMode === 'auto' ? 'prompt' : 'auto';
            await cfg.update('mode', newMode, vscode.ConfigurationTarget.Global);
            vscode.window.showInformationMessage(
                '文件名规范化模式已切换为: ' + (newMode === 'auto' ? '自动' : '提示确认')
            );
            updateStatusBar();
        }
    );

    // ── 文件创建监听（FileSystemWatcher）─────────────────
    const watcher = vscode.workspace.createFileSystemWatcher('**/*', false, true, false);

    const onCreateDisposable = watcher.onDidCreate(async (uri) => {
        const cfg = getConfig();
        if (!cfg.get('sanitizeOnCreate')) {
            return;
        }
        if (uri.scheme !== 'file' || isIgnored(uri.fsPath)) {
            return;
        }
        // 延迟一小段时间，确保文件写入完成
        setTimeout(() => {
            handleFile(uri, 'create');
        }, 300);
    });

    // ── 文件打开监听 ────────────────────────────────────
    const onOpenDisposable = vscode.workspace.onDidOpenTextDocument((document) => {
        const cfg = getConfig();
        if (!cfg.get('checkOnOpen')) {
            return;
        }
        if (document.uri.scheme !== 'file' || isIgnored(document.uri.fsPath)) {
            return;
        }
        // 延迟，避免阻塞编辑器加载
        setTimeout(() => {
            handleFile(document.uri, 'open');
        }, 500);
    });

    // ── 文件保存后监听（保存/另存为后检测文件名）──────────
    const onPostSaveDisposable = vscode.workspace.onDidSaveTextDocument((document) => {
        const cfg = getConfig();
        if (!cfg.get('checkOnSave')) {
            return;
        }
        if (document.uri.scheme !== 'file' || isIgnored(document.uri.fsPath)) {
            return;
        }
        // 保存后立即检查：如果是刚保存的 untitled 文件用了有问题的名字，
        // 此时是第一次有机会检测到
        setTimeout(() => {
            handleFile(document.uri, 'save');
        }, 200);
    });

    // ── 文件关闭时清理缓存 ──────────────────────────────
    const onCloseDisposable = vscode.workspace.onDidCloseTextDocument((document) => {
        processedFiles.delete(document.uri.fsPath);
        pendingChecks.delete(document.uri.fsPath);
    });

    // ── 状态栏 ──────────────────────────────────────────
    const statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        100
    );
    statusBarItem.show();

    function updateStatusBar() {
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.document.uri.scheme !== 'file') {
            // 没有打开文件或为 untitled buffer
            statusBarItem.text = '$(file) Sanitize';
            statusBarItem.tooltip = 'Sanitize Filename';
            statusBarItem.command = 'sanitizeFilename.toggleAutoMode';
            return;
        }

        const fname = path.basename(editor.document.uri.fsPath);
        const isZh = vscode.env.language.startsWith('zh');
        if (needsSanitization(fname)) {
            statusBarItem.text = '$(error) ' + (isZh ? '规范文件名' : 'Sanitize');
            statusBarItem.tooltip = (isZh ? '点击规范化: ' : 'Click to sanitize: ') + fname + ' → ' + sanitizeFilename(fname);
            statusBarItem.command = 'sanitizeFilename.sanitizeCurrent';
        } else {
            statusBarItem.text = '$(pass) ' + (isZh ? '文件名规范' : 'Filename OK');
            statusBarItem.tooltip = isZh ? '文件名规范，无需处理' : 'Filename is clean, no action needed';
            statusBarItem.command = 'sanitizeFilename.sanitizeCurrent';
        }
    }

    // 切换编辑器标签时更新状态栏
    const onEditorChangeDisposable = vscode.window.onDidChangeActiveTextEditor(() => {
        updateStatusBar();
    });

    updateStatusBar();

    // ── 注册所有 disposable ─────────────────────────────
    context.subscriptions.push(
        sanitizeCurrentCmd,
        sanitizeAllCmd,
        toggleAutoCmd,
        watcher,
        onCreateDisposable,
        onOpenDisposable,
        onPostSaveDisposable,
        onCloseDisposable,
        onEditorChangeDisposable,
        statusBarItem
    );
}

/**
 * 扩展停用
 */
export function deactivate() {
    console.log('[Sanitize Filename] Extension deactivated');
    processedFiles.clear();
    pendingChecks.clear();
}
