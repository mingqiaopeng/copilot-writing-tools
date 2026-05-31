#!/usr/bin/env python3
"""量化分析引擎 — 对中文文本进行定量指标计算，输出 JSON"""

import sys
import json
import io

# 确保 Windows 下 stdout 输出 UTF-8
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import re
import os
from collections import Counter
from math import sqrt

# ============================================================
# 虚词表（介词 + 连词 + 助词 + 语气词）
# ============================================================
FUNCTION_WORDS = [
    # 介词
    "在", "把", "被", "从", "以", "向", "对", "于", "与", "跟", "同",
    "将", "让", "给", "叫", "按", "照", "据", "凭", "沿", "顺",
    "朝", "往", "到", "由", "经", "通过",
    # 连词
    "但", "而", "却", "且", "或", "并", "因为", "所以", "如果",
    "虽然", "然而", "而且", "不过", "于是", "因此", "接着",
    "然后", "否则", "即使", "尽管", "无论", "除非",
    # 助词
    "的", "地", "得", "了", "着", "过", "之", "所", "者", "似的",
    # 语气词
    "呢", "吗", "吧", "啊", "嘛", "呗", "呀", "哦", "哟", "啦",
    "么", "而已", "罢", "也罢",
]

# ============================================================
# 感情标点
# ============================================================
EMOTION_PUNCT = set("！？……")

# ============================================================
# 停用词（高频词统计排除）
# ============================================================
STOP_WORDS = {
    "的", "地", "得", "了", "着", "过", "在", "把", "被", "从", "以",
    "向", "对", "于", "与", "和", "跟", "同", "但", "而", "却", "且",
    "或", "并", "因为", "所以", "如果", "虽然", "然而", "而且",
    "呢", "吗", "吧", "啊", "嘛", "呗", "呀", "哦", "哟", "啦", "么",
    "一", "不", "这", "那", "是", "有", "人", "个", "上", "中", "下",
    "大", "来", "去", "到", "说", "看", "想", "要", "会", "能", "好",
    "很", "也", "都", "就", "它", "他", "她", "我", "你", "们",
    "什么", "怎么", "哪", "这个", "那个", "这些", "那些", "自己",
    "可以", "没有", "已经", "还是", "不是", "就是", "一个", "一种",
    "他们", "我们", "你们", "她们", "它们",
}


def strip_frontmatter(text):
    """移除 YAML frontmatter (--- ... ---)"""
    t = text.strip()
    if t.startswith("---"):
        end = t.find("---", 3)
        if end != -1:
            return t[end + 3 :].strip()
    return t


def strip_headings(text):
    """移除 markdown 标题行"""
    return "\n".join(
        l for l in text.split("\n") if not re.match(r"^#{1,6}\s", l.strip())
    )


def count_chars(text):
    """统计字符数（不含空白）"""
    return len(re.sub(r"\s", "", text))


def get_paragraphs(text):
    """提取段落（剔除标题行和过短行，按空行分割）"""
    cleaned = strip_headings(text)
    paras = re.split(r"\n{2,}", cleaned.strip())
    return [p.strip() for p in paras if count_chars(p) > 10]


def split_sentences(text, sep_pattern):
    """按分隔符切句"""
    parts = sep_pattern.split(text)
    return [s.strip() for s in parts if s.strip() and count_chars(s) > 1]


def count_func_words(text):
    """统计虚词总出现次数"""
    total = 0
    for w in FUNCTION_WORDS:
        total += text.count(w)
    return total


def count_emotion_punct(text):
    """统计感情标点出现次数"""
    return sum(1 for c in text if c in EMOTION_PUNCT)


def count_sep_punct(text):
    """统计标点句分隔符总数（。！？，、；：……）"""
    return len(re.findall(r"[。！？，、；：……]", text))


def stddev(values):
    """标准差"""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sqrt(sum((x - mean) ** 2 for x in values) / len(values))


def get_pos_stats(text):
    """使用 jieba 词性标注，返回形/副统计"""
    try:
        import jieba.posseg as pseg

        words = list(pseg.cut(text))
        meaningful = [w for w in words if len(w.word.strip()) >= 1]
        total = len(meaningful)
        adj_count = len([w for w in meaningful if w.flag in ("a", "ad", "an")])
        adv_count = len([w for w in meaningful if w.flag == "d"])
        return {
            "totalWords": total,
            "adjCount": adj_count,
            "advCount": adv_count,
            "adjAdvRatio": round((adj_count + adv_count) / total, 4) if total > 0 else 0,
            "method": "jieba-posseg",
        }
    except ImportError:
        return {
            "totalWords": 0,
            "adjCount": 0,
            "advCount": 0,
            "adjAdvRatio": None,
            "method": "jieba-unavailable",
        }


def get_top_keywords(text, n=6):
    """高频词（使用 jieba 分词，排除停用词和单字）"""
    try:
        import jieba

        words = list(jieba.cut(text))
        filtered = [
            w.strip()
            for w in words
            if len(w.strip()) >= 2 and w.strip() not in STOP_WORDS
        ]
        counter = Counter(filtered)
        return [word for word, _ in counter.most_common(n)]
    except ImportError:
        return []


def analyze(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    body = strip_frontmatter(raw)
    body_no_headings = strip_headings(body)
    paragraphs = get_paragraphs(body)

    total_chars = count_chars(body)

    # ---- 完整句 ----
    FULL_SEP = re.compile(r"[。！？]")
    full_sentences = split_sentences(body_no_headings, FULL_SEP)
    full_lens = [count_chars(s) for s in full_sentences]

    # ---- 标点句 ----
    PUNCT_SEP = re.compile(r"[。！？，、；：……]")
    punct_sentences = split_sentences(body_no_headings, PUNCT_SEP)
    punct_lens = [count_chars(s) for s in punct_sentences]

    # ---- 段落 ----
    para_lens = [count_chars(p) for p in paragraphs]

    # ---- 虚词 ----
    func_count = count_func_words(body)
    func_ratio = round(func_count / total_chars, 4) if total_chars > 0 else 0

    # ---- 感情标点 ----
    emotion_count = count_emotion_punct(body)
    sep_count = count_sep_punct(body)
    emotion_ratio = round(emotion_count / sep_count, 4) if sep_count > 0 else 0

    # ---- 词性 ----
    pos = get_pos_stats(body)

    # ---- 高频词 ----
    keywords = get_top_keywords(body)

    return {
        "totalChars": total_chars,
        "paragraphCount": len(paragraphs),
        "fullSentenceCount": len(full_sentences),
        "punctSentenceCount": len(punct_sentences),
        "avgFullSentenceLen": round(sum(full_lens) / len(full_lens), 1) if full_lens else 0,
        "stdFullSentenceLen": round(stddev(full_lens), 1),
        "avgPunctSentenceLen": round(sum(punct_lens) / len(punct_lens), 1) if punct_lens else 0,
        "stdPunctSentenceLen": round(stddev(punct_lens), 1),
        "avgParaLen": round(sum(para_lens) / len(para_lens), 1) if para_lens else 0,
        "stdParaLen": round(stddev(para_lens), 1),
        "funcWordRatio": func_ratio,
        "emotionPunctRatio": emotion_ratio,
        "adjAdvRatio": pos["adjAdvRatio"],
        "adjAdvMethod": pos["method"],
        "topKeywords": keywords,
        "posDetail": {
            "totalWords": pos["totalWords"],
            "adjCount": pos["adjCount"],
            "advCount": pos["advCount"],
        },
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {"error": "Usage: python analyze.py <filepath>"},
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(
            json.dumps(
                {"error": f"File not found: {filepath}"},
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    result = analyze(filepath)
    print(json.dumps(result, ensure_ascii=False, indent=2))
