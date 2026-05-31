#!/usr/bin/env python3
"""量化分析引擎 — 对中文文本进行定量指标计算，输出 JSON

用法:
  python analyze.py <filepath>              # 全量分析
  python analyze.py <filepath> --section    # 分段分析（用于跨章节风格对比）
"""

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

# ============================================================
# 正式度标记词
# ============================================================
FORMAL_SUFFIXES = re.compile(
    r".*(性|化|度|型|式|主义|观|论|制|体|学|法|权|力|率|额|值)$"
)
CLASSICAL_PARTICLES = set("之其所谓者也矣焉乎耳")


def _import_jieba():
    """延迟导入 jieba，方便检测是否可用"""
    try:
        import jieba
        import jieba.posseg as pseg
        import jieba.analyse

        return jieba, pseg, jieba.analyse
    except ImportError:
        return None, None, None


# ============================================================
# 基础工具
# ============================================================


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
    """提取段落（剔除标题行和过短行）

    优先按空行（\\n{2,}）切段。若切出段落数 ≤2 但原文换行数 ≥5，
    说明段落之间无空行（常见于中文文稿），回退为按单换行切段。
    """
    cleaned = strip_headings(text).strip()

    # 先试空行切段
    paras = [p.strip() for p in re.split(r"\n{2,}", cleaned) if p.strip()]
    paras = [p for p in paras if count_chars(p) > 15]

    # 回退：空行切段太少，但原文有很多换行 → 按单行切
    line_count = cleaned.count("\n") + 1
    if len(paras) <= 2 and line_count >= 5:
        lines = [l.strip() for l in cleaned.split("\n")]
        # 过滤：空行、markdown标题、过短行（标题）、纯标点/分隔线
        paras = [
            l for l in lines
            if l
            and count_chars(l) > 15
            and not re.match(r"^#{1,6}\s", l)
            and not re.match(r"^[=\-—－\*]{3,}$", l)
        ]

    return paras


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
    """统计标点句分隔符总数"""
    return len(re.findall(r"[。！？，、；：……]", text))


def stddev(values):
    """标准差"""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sqrt(sum((x - mean) ** 2 for x in values) / len(values))


# ============================================================
# jieba 依赖的分析函数
# ============================================================


def get_pos_stats(text):
    """词性标注 → 形/副统计"""
    _, pseg, _ = _import_jieba()
    if pseg is None:
        return {"totalWords": 0, "adjCount": 0, "advCount": 0,
                "adjAdvRatio": None, "method": "jieba-unavailable"}

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


def get_top_keywords(text, n=6):
    """词频关键词（jieba 分词 + 停用词排除）"""
    jieba, _, _ = _import_jieba()
    if jieba is None:
        return []
    words = list(jieba.cut(text))
    filtered = [
        w.strip()
        for w in words
        if len(w.strip()) >= 2 and w.strip() not in STOP_WORDS
    ]
    counter = Counter(filtered)
    return [word for word, _ in counter.most_common(n)]


def get_textrank_keywords(text, n=6):
    """TextRank 关键词提取（比词频更准确）"""
    _, _, analyse = _import_jieba()
    if analyse is None:
        return []
    return analyse.textrank(text, topK=n, withWeight=False)


def get_word_count(text):
    """jieba 分词词数"""
    jieba, _, _ = _import_jieba()
    if jieba is None:
        return 0
    words = list(jieba.cut(text))
    return len([w for w in words if len(w.strip()) >= 1])


def get_lexical_diversity(text):
    """词汇多样性 = 不重复词数 / 总词数"""
    jieba, _, _ = _import_jieba()
    if jieba is None:
        return None
    words = [w.strip() for w in jieba.cut(text) if len(w.strip()) >= 2]
    if not words:
        return 0.0
    return round(len(set(words)) / len(words), 4)


def get_de_density(text):
    """"的"字密度 = 每千字"的"字数"""
    chars = count_chars(text)
    if chars == 0:
        return 0.0
    de_count = text.count("的")
    return round(de_count / chars * 1000, 1)


def get_formal_ratio(text):
    """正式词比率 = 含正式标记的词数 / 总词数"""
    jieba, _, _ = _import_jieba()
    if jieba is None:
        return None
    words = [w.strip() for w in jieba.cut(text) if len(w.strip()) >= 1]
    if not words:
        return 0.0
    formal_count = 0
    for w in words:
        if FORMAL_SUFFIXES.match(w):
            formal_count += 1
        elif w in CLASSICAL_PARTICLES:
            formal_count += 1
    return round(formal_count / len(words), 4)


def get_word_length_distribution(text):
    """词长分布 — 单字词/双字词/三字词/四字及以上 各占比"""
    jieba, _, _ = _import_jieba()
    if jieba is None:
        return None
    words = [w.strip() for w in jieba.cut(text) if len(w.strip()) >= 1]
    if not words:
        return {"single": 0, "double": 0, "triple": 0, "quadPlus": 0, "totalWords": 0}
    total = len(words)
    single = len([w for w in words if len(w) == 1])
    double = len([w for w in words if len(w) == 2])
    triple = len([w for w in words if len(w) == 3])
    quad = len([w for w in words if len(w) >= 4])
    return {
        "single": round(single / total, 4),
        "double": round(double / total, 4),
        "triple": round(triple / total, 4),
        "quadPlus": round(quad / total, 4),
        "totalWords": total,
    }


def get_pos_distribution(text):
    """词性分布全景 — 名词/动词/形容词/副词/虚词(介+连+助)/其他 占比"""
    _, pseg, _ = _import_jieba()
    if pseg is None:
        return None
    words = list(pseg.cut(text))
    meaningful = [w for w in words if len(w.word.strip()) >= 1]
    if not meaningful:
        return {"noun": 0, "verb": 0, "adj": 0, "adv": 0, "func": 0, "other": 0, "totalWords": 0}

    total = len(meaningful)

    # 名词: n/ng/nr/ns/nt/nz/nrt
    noun = len([w for w in meaningful if w.flag.startswith("n")])
    # 动词: v/vd/vn/vg/vi/vx
    verb = len([w for w in meaningful if w.flag.startswith("v")])
    # 形容词: a/ad/an/ag
    adj = len([w for w in meaningful if w.flag.startswith("a")])
    # 副词: d/dg
    adv = len([w for w in meaningful if w.flag.startswith("d")])
    # 虚词: p(介词) + c(连词) + u(助词)
    func = len([w for w in meaningful if w.flag.startswith(("p", "c", "u"))])
    other = total - noun - verb - adj - adv - func

    return {
        "noun": round(noun / total, 4),
        "verb": round(verb / total, 4),
        "adj": round(adj / total, 4),
        "adv": round(adv / total, 4),
        "func": round(func / total, 4),
        "other": round(other / total, 4),
        "totalWords": total,
    }


def get_chengyu_stats(text):
    """四字格（成语/固定搭配）检测

    策略：jieba 分词后筛选四字词，区分词典收录的（倾向成语）和未收录的（倾向固定搭配）。
    返回每千词四字格密度、Top N 高频四字格及其出现次数。
    """
    jieba, _, _ = _import_jieba()
    if jieba is None:
        return None

    words = [w.strip() for w in jieba.cut(text) if len(w.strip()) >= 1]
    if not words:
        return {"densityPerK": 0, "totalCount": 0, "topPhrases": [], "totalWords": 0}

    quad_words = [w for w in words if len(w) == 4]
    # 尝试区分：在 jieba 词典中的四字词通常是成语或固定搭配
    # jieba 有 get_dict_file() 但不可靠，改用 FREQ 属性检查
    in_dict = []
    not_in_dict = []
    for w in quad_words:
        # jieba 内部词频表：高频四字词通常是成语/固定搭配
        freq = jieba.get_FREQ(w)
        if freq is not None:
            in_dict.append(w)
        else:
            not_in_dict.append(w)

    total_words = len(words)
    density = round(len(quad_words) / total_words * 1000, 1) if total_words > 0 else 0

    # Top 四字格（按出现频率，合并 in-dict 和 not-in-dict）
    all_counter = Counter(quad_words)
    top_all = [{"phrase": w, "count": c, "inDict": w in set(in_dict)}
               for w, c in all_counter.most_common(10)]

    return {
        "densityPerK": density,
        "totalCount": len(quad_words),
        "inDictCount": len(in_dict),
        "notInDictCount": len(not_in_dict),
        "topPhrases": top_all,
        "totalWords": total_words,
    }


def get_paragraph_similarity(paragraphs):
    """段落间 Jaccard 相似度矩阵

    返回上三角矩阵 [{i, j, score}, ...]，按 score 降序排列。
    仅返回 score >= 0.3 的条目（0.3 以下视为不相似）。
    """
    jieba, _, _ = _import_jieba()
    if jieba is None:
        return {"method": "jieba-unavailable", "pairs": []}

    n = len(paragraphs)
    if n < 2:
        return {"method": "jieba-jaccard", "pairs": []}

    # 每段转词集
    word_sets = []
    for p in paragraphs:
        words = {w.strip() for w in jieba.cut(p)
                 if len(w.strip()) >= 2 and w.strip() not in STOP_WORDS}
        word_sets.append(words)

    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            a, b = word_sets[i], word_sets[j]
            if not a or not b:
                continue
            intersection = len(a & b)
            union = len(a | b)
            score = round(intersection / union, 4) if union > 0 else 0.0
            if score >= 0.3:
                pairs.append({"i": i + 1, "j": j + 1, "score": score})

    pairs.sort(key=lambda x: x["score"], reverse=True)
    return {"method": "jieba-jaccard", "pairs": pairs}


def get_section_analysis(paragraphs):
    """逐段分析 — 用于跨章节风格对比

    为每个段落计算完整风格指纹：词长分布、词性分布、四字格密度、正式词比率、句长等
    """
    results = []
    for i, p in enumerate(paragraphs):
        chars = count_chars(p)
        results.append({
            "section": i + 1,
            "chars": chars,
            "wordCount": get_word_count(p),
            "funcWordRatio": round(count_func_words(p) / chars, 4) if chars > 0 else 0,
            "formalRatio": get_formal_ratio(p),
            "deDensity": get_de_density(p),
            "avgPunctSentenceLen": _avg_punct_sent_len(p),
            "wordLengthDist": get_word_length_distribution(p),
            "posDist": get_pos_distribution(p),
            "chengyuStats": get_chengyu_stats(p),
            "preview": p[:60].replace("\n", " "),
        })
    return results


def _avg_punct_sent_len(text):
    PUNCT_SEP = re.compile(r"[。！？，、；：……]")
    sents = split_sentences(text, PUNCT_SEP)
    lens = [count_chars(s) for s in sents]
    return round(sum(lens) / len(lens), 1) if lens else 0


# ============================================================
# 主分析入口
# ============================================================


def analyze(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    body = strip_frontmatter(raw)
    body_no_headings = strip_headings(body)
    paragraphs = get_paragraphs(body)

    total_chars = count_chars(body)
    word_count = get_word_count(body)

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

    # ---- 关键词（词频 + TextRank） ----
    freq_keywords = get_top_keywords(body)
    textrank_keywords = get_textrank_keywords(body)

    # ---- 词汇级指标 ----
    lexical_diversity = get_lexical_diversity(body)
    de_density = get_de_density(body)
    formal_ratio = get_formal_ratio(body)

    # ---- 段落相似度 ----
    para_sim = get_paragraph_similarity(paragraphs)

    # ---- 风格指纹 ----
    wl_dist = get_word_length_distribution(body)
    pos_dist = get_pos_distribution(body)
    chengyu = get_chengyu_stats(body)

    return {
        # 基础数据
        "totalChars": total_chars,
        "wordCount": word_count,
        "paragraphCount": len(paragraphs),
        "fullSentenceCount": len(full_sentences),
        "punctSentenceCount": len(punct_sentences),

        # 句长
        "avgFullSentenceLen": round(sum(full_lens) / len(full_lens), 1) if full_lens else 0,
        "stdFullSentenceLen": round(stddev(full_lens), 1),
        "avgPunctSentenceLen": round(sum(punct_lens) / len(punct_lens), 1) if punct_lens else 0,
        "stdPunctSentenceLen": round(stddev(punct_lens), 1),

        # 段长
        "avgParaLen": round(sum(para_lens) / len(para_lens), 1) if para_lens else 0,
        "stdParaLen": round(stddev(para_lens), 1),

        # 比率
        "funcWordRatio": func_ratio,
        "emotionPunctRatio": emotion_ratio,
        "adjAdvRatio": pos["adjAdvRatio"],
        "adjAdvMethod": pos["method"],

        # 词汇级
        "lexicalDiversity": lexical_diversity,
        "deDensity": de_density,
        "formalRatio": formal_ratio,

        # 风格指纹
        "wordLengthDist": wl_dist,
        "posDist": pos_dist,
        "chengyuStats": chengyu,
        "chengyuDensityPerK": chengyu["densityPerK"] if chengyu else None,
        "chengyuTotal": chengyu["totalCount"] if chengyu else None,
        "chengyuTop10": [f"{p['phrase']}({p['count']})" for p in chengyu["topPhrases"]] if chengyu else [],

        # 关键词
        "freqKeywords": freq_keywords,
        "textrankKeywords": textrank_keywords,

        # 段落相似度
        "paragraphSimilarity": para_sim,

        # 词性详情（保留向后兼容）
        "posDetail": {
            "totalWords": pos["totalWords"],
            "adjCount": pos["adjCount"],
            "advCount": pos["advCount"],
        },
    }


def analyze_sections(filepath):
    """分段分析模式 — 返回逐段风格特征"""
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()
    body = strip_frontmatter(raw)
    paragraphs = get_paragraphs(body)
    return {
        "paragraphCount": len(paragraphs),
        "sections": get_section_analysis(paragraphs),
        "similarity": get_paragraph_similarity(paragraphs),
    }


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps(
            {"error": "Usage: python analyze.py <filepath> [--section]"},
            ensure_ascii=False,
        ))
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(json.dumps(
            {"error": f"File not found: {filepath}"},
            ensure_ascii=False,
        ))
        sys.exit(1)

    if "--section" in sys.argv:
        result = analyze_sections(filepath)
    else:
        result = analyze(filepath)

    print(json.dumps(result, ensure_ascii=False, indent=2))
