#!/usr/bin/env python3
"""搜索优秀修辞句子库 — 按关键词和标签匹配，返回 top N 结果

用法:
  python search_rhetoric.py --query "核心关键词" [--tags "比喻,排比"] [--count 5]
"""

import sys
import json
import os
import re
import argparse

ASSETS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "good-sentences.jsonl")


def load_db(filepath):
    """加载 jsonl 句子库"""
    if not os.path.exists(filepath):
        print(json.dumps({"error": f"句子库不存在: {filepath}", "results": []}, ensure_ascii=False))
        sys.exit(1)

    entries = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get("content"):
                    entries.append({"text": obj["content"], "tags": obj.get("tags", [])})
            except json.JSONDecodeError:
                continue
    return entries


def score_entry(entry, query_terms, tag_filter):
    """计算单条句子与查询的匹配得分

    得分 = 关键词命中率 (0-1) + 标签命中加分 (0-0.3)
    """
    text_lower = entry["text"].lower()
    item_tags = [t.lower() for t in entry.get("tags", [])]

    # 关键词匹配得分：命中关键词数 / 总关键词数
    match_count = sum(1 for t in query_terms if t in text_lower)
    text_score = match_count / len(query_terms) if query_terms else 0

    # 标签加分：命中标签比例 * 0.3
    tag_bonus = 0.0
    if tag_filter:
        tag_match = sum(1 for t in tag_filter if t in item_tags)
        tag_bonus = (tag_match / len(tag_filter)) * 0.3

    return text_score + tag_bonus


def main():
    parser = argparse.ArgumentParser(description="搜索优秀修辞句子库")
    parser.add_argument("--query", required=True, help="搜索关键词，空格分隔")
    parser.add_argument("--tags", default="", help="过滤标签，逗号分隔")
    parser.add_argument("--count", type=int, default=5, help="返回结果数量")
    parser.add_argument("--db", default=ASSETS_PATH, help="句子库路径（默认 assets/good-sentences.jsonl）")
    args = parser.parse_args()

    db = load_db(args.db)
    if not db:
        print(json.dumps({"message": "句子库为空", "results": []}, ensure_ascii=False))
        return

    query_terms = [t.lower() for t in args.query.split() if t]
    tag_filter = [t.strip().lower() for t in re.split(r"[,，]", args.tags) if t.strip()] if args.tags else []

    scored = []
    for entry in db:
        # 标签预过滤：若指定了标签过滤，至少命中一个标签才进入评分
        if tag_filter:
            item_tags = [t.lower() for t in entry.get("tags", [])]
            if not any(t in item_tags for t in tag_filter):
                continue
        score = score_entry(entry, query_terms, tag_filter)
        if score > 0:
            scored.append({"text": entry["text"], "tags": entry.get("tags", []), "score": round(score, 4)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:args.count]

    result = {
        "total": len(scored),
        "count": len(top),
        "query": args.query,
        "tags": args.tags,
        "results": top,
        "message": f"共找到 {len(scored)} 条匹配，展示前 {len(top)} 条",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
