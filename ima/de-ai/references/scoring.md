# de-ai · AI 味评分体系

> 需要给「AI 味」一个量化总分时，从以下三套体系中任选其一。评分结果用于自测与复核，不替代逐项改写。

---

## 一、累加扣分制（the-antislop）

| 模式 | 分值 |
|------|------|
| Tier 1 短语（delve / game-changer / revolutionary / unlock potential / 值得注意的是 / 今天的 XX landscape / moreover / furthermore / cutting-edge / pivotal moment / tapestry / intricate / showcase / vibrant / interplay / garner / align with） | 每处 +3 |
| Tier 2 重复（here's the thing / at the end of the day / the bottom line / 配对形容词 comprehensive and thorough / 模板开场） | 重复出现 +2 |
| Tier 3 聚簇（转折词开头成癖 / 企业黑话 robust-seamless-scalable） | 成簇 +2 |
| 星座测试失败 | +5 |
| 碎片 spam（短句连发） | +4 |
| 伪造个性 | +4 |

**判读**：0-5 低风险 ｜ 6-12 中风险（需大幅编辑）｜ 13+ 高风险（大概率未修饰的 AI 文本）

## 二、五维评分制（stop-slop，各 1-10 分，满分 50）

| 维度 | 核心问题 | 低分（1-3）表现 | 高分（8-10）表现 |
|------|----------|------------------|------------------|
| Directness 直接性 | 在陈述，还是在宣布？ | 清嗓子、铺垫、预告 | 直接陈述 |
| Rhythm 节奏 | 句长自然变化，还是像节拍器？ | 等长句连续 | 长短交错、段尾各异 |
| Trust 信任 | 尊重读者智商吗？ | 手把手解释、过度辩护 | 相信读者 |
| Authenticity 真实 | 听起来像人写的吗？ | AI 模式可检出 | 有人味和立场 |
| Density 密度 | 有没有可删的？ | 填充与冗余 | 每个词都在挣钱 |

**判读**：<35/50 → 重写。

快速自检：
- 连续三句等长？打断一句。
- 段落以精练短句收尾？换个收法。
- 破折号出现在揭示句前？删掉。
- 在解释比喻？相信它能落地。

## 三、统计评分制（0-100，可程序化）

- 综合分 = 模式分 + **均匀度分**（uniformity）
- 统计指标：
  - **burstiness**（句长方差）——AI 倾向复用相同 3 词短语、句长集中
  - **type-token ratio**（词汇多样性）
  - **FK 可读性**——AI 倾向稳定在 8-12 年级水平，人类会波动
- 分级：0-25 🟢 基本像人 ｜ 26-50 🟡 轻度 AI ｜ 51-75 🟠 中度 ｜ 76-100 🔴 重度

---

## 附：实证背景（这些规则为什么可信）

| 研究 | 样本 | 发现 |
|------|------|------|
| 芬兰作文研究 | 56,878 篇作文 | 「delve」用量在 ChatGPT 之后增加 **10.45 倍** |
| Georgia Tech 论文分析 | 1.683 亿篇文章 | 「delve」从 0.31/千词 → **7.9/千词**（2024 Q1） |
| 生物医学文献研究 | 2023-2024 | delve / realm / underscore 共现增加最高 **85 倍** |
| Louis Abraham PR 分析 | 461,000+ GitHub PR | 2026 年 **45% 的人类署名 PR** 共享同一 LLM 词汇簇：load-bearing（+123x）、seam、quietly、latent、genuine |
| Copyleaks 文体指纹研究 | — | 统计特征（burstiness 等）可稳定区分人机文本 |
