#!/usr/bin/env python3
"""
提取 VS Code Copilot Chat 历史，过滤出与本项目 Agent/Skill 相关的对话。
输出为 Markdown 文件便于分析。

用法:
  python extract-copilot-logs.py           # 默认过滤，只导出匹配的对话
  python extract-copilot-logs.py --all     # 不过滤，导出全部
  python extract-copilot-logs.py --list    # 只列出不导出
  python extract-copilot-logs.py --clean   # 清空所有历史记录（需确认）
"""

import argparse
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# ── 项目关键词 ──
PROJECT_KEYWORDS = [
    # Agent 名称
    '批判家', '分析师', '点子王', '档案员',
    # Skill 名称
    '优化句式', '校对勘误', '写中心句', '摘要生成', '标题优化',
    '段落重组', '大纲生成', '增加过渡', '缩减篇幅', '扩充篇幅',
    '合并段落', '拆分段落', '简化修辞', '神来之笔', '增加修辞',
    '去除标签', '换个风格', '传达提纲',
    # Agent 触发词
    '批判性审核', '批判审核', '挑毛病', '找问题', '严格审核',
    '严厉审核', '审稿', '审一下', '有什么问题', '哪里不好',
    '批评一下', '批判一下', '最高标准', '鸡蛋里挑骨头',
    '严格把关', '质量检查', '逻辑审查', '文法检查', '找错',
    '分析一下', '分析文章',
    # Skill 触发词
    '句式调整', '英式中文', '翻译腔', '改句式', '句子太啰嗦',
    '中文不够地道', '欧化句式', '的的不休', '优化句子', '改句子',
    '润色句子', '改改句子',
    # 通用
    '按勘误表修改', '勘误表', '什么毛病',
]


# ── 路径 ──
APPDATA = os.environ.get('APPDATA', '')
SESSION_DIR = os.path.join(APPDATA, 'Code', 'User', 'globalStorage', 'emptyWindowChatSessions')
STORAGE_ROOTS = [
    SESSION_DIR,
    # 旧版本：workspace 级别
]


def find_jsonl_sessions(roots):
    """扫描所有 JSONL 会话文件"""
    sessions = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for fname in sorted(os.listdir(root), reverse=True):
            if fname.endswith('.jsonl'):
                fpath = os.path.join(root, fname)
                mtime = os.path.getmtime(fpath)
                sessions.append({
                    'path': fpath,
                    'id': fname.replace('.jsonl', ''),
                    'mtime': datetime.fromtimestamp(mtime),
                    'requests': [],
                    'title': '',
                })
    return sessions


def read_jsonl_session(session):
    """读取单个 JSONL 文件的会话数据"""
    with open(session['path'], 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            kind = data.get('kind')
            if kind == 0:  # 会话元数据
                v = data.get('v', {})
                session['title'] = v.get('title', v.get('inputState', {}).get('inputText', ''))
                # 获取请求列表（对话轮次）
                for req in v.get('requests', []):
                    turn = parse_request(req)
                    if turn:
                        session['requests'].append(turn)
            elif kind == 1:  # metadata
                pass


def parse_request(req):
    """解析一个请求（即一轮对话：用户消息 + 助手回复）"""
    msg = req.get('message', {})
    user_text = msg.get('text', '')
    if not user_text:
        return None

    # 提取助手回复中的文本
    assistant_texts = []
    for item in req.get('response', []):
        content = item.get('content', {})
        kind = item.get('kind', '')
        if kind == 'text' and 'text' in content:
            t = content['text']
            if t and len(t) > 20:  # 忽略太短的片段
                assistant_texts.append(t)
        elif kind == 'progressStart':
            # 跳过 mcpServersStarting / progressStart 等
            pass
    # Tool calls / MCP 响应 / 内联编辑 不保存完整的 assistant 文本

    return {
        'user': user_text,
        'assistant': '\n\n'.join(assistant_texts),
        'model': req.get('modelId', ''),
        'agent': req.get('agent', ''),
    }


def session_matches(session, keywords):
    """检查会话是否命中关键词"""
    text = f"{session['title']} "
    for t in session['requests']:
        text += t['user'] + ' '
    text_lower = text.lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            return True
    return False


def matched_keywords(text, keywords):
    """返回文本中命中的关键词列表"""
    return [kw for kw in keywords if kw.lower() in text.lower()]


def export_markdown(sessions, output_dir, all_flag):
    """将会话导出为 Markdown 文件"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    exported = []

    for session in sessions:
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', session.get('title', 'untitled'))
        if len(safe_name) > 60:
            safe_name = safe_name[:60]
        if not safe_name.strip('_ \t'):
            safe_name = f"chat_{session['id'][:8]}"

        out_file = os.path.join(output_dir, f"copilot-chat_{timestamp}_{safe_name}.md")

        lines = []
        if all_flag:
            lines.append("# Copilot Chat 导出")
        else:
            lines.append("# Copilot Chat 导出（仅 Agent/Skill 相关片段）")

        lines.extend([
            "",
            f"来源: {session.get('title', '未命名')}",
            f"会话 ID: {session['id']}",
            f"导出于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"对话轮次: {len(session['requests'])}",
            "",
            "---",
            "",
        ])

        for turn in session['requests']:
            user_text = turn['user']

            if all_flag:
                lines.append(f"## User\n")
                lines.append(f"{user_text}\n")
                lines.append("---\n")
            else:
                # 过滤模式下只在命中时输出，并标注关键词
                u_kws = matched_keywords(user_text, PROJECT_KEYWORDS)
                if not u_kws:
                    continue
                tag = f"[{', '.join(u_kws)}]"
                lines.append(f"## User {tag}\n")
                lines.append(f"{user_text}\n")
                lines.append("---\n")

        content = '\n'.join(lines)

        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(content)

        exported.append(out_file)

    return exported


def main():
    parser = argparse.ArgumentParser(description='提取 VS Code Copilot Chat 历史')
    parser.add_argument('--all', action='store_true', help='导出全部对话（不过滤）')
    parser.add_argument('--list', action='store_true', help='只列出不导出')
    parser.add_argument('--clean', action='store_true', help='清空所有 Copilot Chat 历史记录')
    parser.add_argument('-o', '--output', default='.', help='输出目录（默认当前目录）')
    args = parser.parse_args()

    # ── --clean 模式：清空历史 ──
    if args.clean:
        print("=" * 50)
        print("即将清空所有 Copilot Chat 历史记录！")
        print("=" * 50)
        print(f"  删除: {len(os.listdir(SESSION_DIR)) if os.path.isdir(SESSION_DIR) else 0} 个会话文件")
        print("  重置: 会话索引 chat.ChatSessionStore.index")
        print()
        confirm = input("确认清空？此操作不可撤销 (yes/NO): ").strip().lower()
        if confirm != 'yes':
            print("已取消。")
            return

        deleted = 0
        if os.path.isdir(SESSION_DIR):
            for fname in os.listdir(SESSION_DIR):
                if fname.endswith('.jsonl'):
                    os.remove(os.path.join(SESSION_DIR, fname))
                    deleted += 1
            print(f"  [OK] 已删除 {deleted} 个会话文件")

        # 清空会话索引
        state_db = os.path.join(APPDATA, 'Code', 'User', 'globalStorage', 'state.vscdb')
        if os.path.isfile(state_db):
            try:
                conn = sqlite3.connect(state_db)
                conn.execute("DELETE FROM ItemTable WHERE [key]='chat.ChatSessionStore.index'")
                conn.commit()
                affected = conn.total_changes
                conn.close()
                if affected > 0:
                    print("  [OK] 已重置会话索引")
                else:
                    print("  [--] 会话索引不存在，无需处理")
            except Exception as e:
                print(f"  [WARN] 无法重置会话索引: {e}")
        else:
            print("  [--] state.vscdb 不存在，跳过索引清理")

        print("\n清空完成。重启 VS Code 后生效。")
        return

    # ── 扫描 ──
    print("正在扫描 Copilot Chat 历史...")
    sessions = find_jsonl_sessions(STORAGE_ROOTS)

    if not sessions:
        print("未找到任何 Copilot Chat 历史记录。")
        print(f"扫描路径:")
        for r in STORAGE_ROOTS:
            print(f"  {r}")
        print("\n" + "=" * 50)
        print("提示：")
        print("  VS Code Copilot Chat 的会话记录存储在全局存储中。")
        print("  确保你至少使用过一次 Copilot Chat 后再试。")
        print("=" * 50)
        return

    # ── 读取并筛选 ──
    matched = []
    for s in sessions:
        read_jsonl_session(s)
        if args.all or session_matches(s, PROJECT_KEYWORDS):
            matched.append(s)

    # 按修改时间排序
    matched.sort(key=lambda s: s['mtime'], reverse=True)

    if not matched:
        print("未找到与 Agent/Skill 相关的 Chat 记录。")
        return

    # ── 列出 ──
    print(f"\n找到 {len(matched)} 条相关会话：\n")
    for i, s in enumerate(matched, 1):
        title = s.get('title', '未命名') or '未命名'
        turns = len(s['requests'])
        if turns > 0:
            # 显示前两句用户输入以帮助识别
            samples = ' | '.join(t['user'][:40] for t in s['requests'][:2])
        else:
            samples = '（无对话记录）'
        print(f"  [{i}] {title}")
        print(f"      {s['mtime'].strftime('%Y-%m-%d %H:%M')} | {turns} 轮 | {samples}")
        print()

    if args.list:
        return

    # ── 选择 ──
    default_n = min(5, len(matched))
    inp = input(f"默认输出最近 {default_n} 条（按 Enter），或输入序号：").strip()

    selected = []
    if not inp:
        selected = matched[:default_n]
    else:
        for part in inp.split(','):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(matched):
                    selected.append(matched[idx])

    if not selected:
        print("未选择任何会话。")
        return

    # ── 导出 ──
    output_dir = os.path.abspath(args.output)
    exported = export_markdown(selected, output_dir, args.all)

    print(f"\n已导出 {len(exported)} 个文件：")
    for f in exported:
        print(f"  [OK] {f}")
    print(f"\n将导出的 .md 文件发给 Claude Code 即可分析 Agent/Skill 表现。")


if __name__ == '__main__':
    main()
