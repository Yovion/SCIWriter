# Introduction 优化说明

## 一、Tags 优化设计

### 新 Tags 体系（7 类）

1. **general_disease_background** - 通用疾病背景（疾病负担、临床重要性、预后异质性）
2. **review_background** - 综述类文章
3. **clinical_progression_or_stage** - 临床进展、分期相关
4. **prognostic_biomarker_signature** - 特定预后签名/模型
5. **transcriptome_screening** - 转录组筛选方法
6. **survival_modeling** - 生存分析建模
7. **mechanism_or_specific_gene** - 机制研究或特定基因功能

### 关键改进

- **不再粗暴标记 disease_background**：特定 signature、特定机制、特定基因类文章不再被标记为通用背景
- **区分综述与研究文章**：综述类文章优先作为背景支撑
- **区分通用背景与特定研究**：临床进展/分期研究 vs 特定分子机制研究

---

## 二、文献重新分类结果

### ✅ 适合第一段疾病背景的文献

**PMID:39153653** (Circular RNAs 综述)
- Tags: `review_background`, `general_disease_background`, `prognostic_biomarker_signature`
- 理由：综述类，开头明确提到 "significant global health concern, poor prognosis for advanced-stage disease"
- **最适合第一段**

**PMID:40239580** (T/N 分期的分子特征)
- Tags: `general_disease_background`, `clinical_progression_or_stage`, `transcriptome_screening`, `survival_modeling`
- 理由：明确提到 "Late-stage cancers associated with greater morbidity and poorer survival"
- **适合第一段和第二段**

**PMID:41234877** (THBS1 作为预后标志物)
- Tags: `general_disease_background`, `prognostic_biomarker_signature`
- 理由：Abstract 开头强调 "prevalent and aggressive... poor prognosis... high incidence and significant mortality"
- **适合第一段**

**PMID:39452555** (基因表达生物标志物综述)
- Tags: `review_background`, `general_disease_background`, `prognostic_biomarker_signature`
- 理由：综述类，提到 "poses a substantial challenge in head and neck oncology"
- **适合第一段**（备选）

**PMID:40642601** (组蛋白乳酸化综述)
- Tags: `review_background`, `general_disease_background`, `mechanism_or_specific_gene`
- 理由：综述类，提到 "common malignant tumor"，但偏机制
- **适合第一段**（备选，但不如前三篇）

---

### ✅ 适合第二段研究现状的文献

**PMID:35910213** (免疫基因组学预后签名)
- Tags: `prognostic_biomarker_signature`, `transcriptome_screening`, `survival_modeling`
- 理由：典型的 DEG + Cox regression 预后筛选研究
- **最适合第二段**

**PMID:40239580** (T/N 分期的分子特征)
- Tags: `general_disease_background`, `clinical_progression_or_stage`, `transcriptome_screening`, `survival_modeling`
- 理由：转录组分析 + 生存标志物筛选
- **适合第二段**

**PMID:34570775** (CIP4 作为预后标志物)
- Tags: `prognostic_biomarker_signature`, `survival_modeling`, `mechanism_or_specific_gene`
- 理由：Cox regression + 生存分析，但聚焦特定基因
- **适合第二段**（备选）

---

### ❌ 不适合通用背景引用的文献

**PMID:40229748** (m6A 调控的铁死亡生物标志物)
- Tags: `prognostic_biomarker_signature`, `mechanism_or_specific_gene`
- 理由：太特定（m6A-ferroptosis pathway, TFRC/RGS4/FTH1），机制导向太强
- **降级：不适合第一段或第二段通用背景**

**PMID:39085122** (HOXA1 与 AKT/mTOR 通路)
- Tags: `mechanism_or_specific_gene`
- 理由：纯机制研究（HOXA1-AKT/mTOR），不适合任何背景陈述
- **降级：不适合任何背景 claim**

**PMID:39893643** (CTSL 与自噬通路)
- Tags: `mechanism_or_specific_gene`
- 理由：纯机制研究（CTSL-IL6-JAK-STAT3），不适合任何背景陈述
- **降级：不适合任何背景 claim**

---

## 三、Claims 绑定优化

### Claim 1: 疾病背景（第一段）

**优化前**：
- supporting_pmids: `35910213`, `40229748`
- 问题：两篇都是特定 signature 研究，不适合支撑"疾病具有临床重要性"这类通用背景句

**优化后**：
- supporting_pmids: `39153653`, `40239580`, `41234877`
- 理由：
  - 39153653：综述，明确提到 "significant global health concern, poor prognosis"
  - 40239580：临床进展研究，提到 "Late-stage cancers... greater morbidity... poorer survival"
  - 41234877：明确提到 "prevalent and aggressive... poor prognosis... high incidence and significant mortality"

### Claim 2: 研究现状（第二段）

**优化前**：
- supporting_pmids: `35910213`, `40229748`, `39085122`
- 问题：40229748 太机制化（m6A-ferroptosis），39085122 纯机制研究（HOXA1-AKT/mTOR）

**优化后**：
- supporting_pmids: `35910213`, `40239580`
- 理由：
  - 35910213：典型的 DEG + Cox regression 预后筛选
  - 40239580：转录组分析 + 生存标志物筛选
  - 两篇都是方法学适配的研究，不过度机制化

### Claim 3: 研究目标（第三段）

**无变化**：
- supporting_pmids: 无（self_description）

---

## 四、Introduction 正文优化

### 第一段（疾病背景）

**优化前**：
> "Laryngeal cancer represents a significant clinical challenge with considerable morbidity and mortality burden [PMID:35910213; PMID:40229748]."

**问题**：
- 语气过强："represents... considerable morbidity and mortality burden"
- 引用不当：35910213 和 40229748 都是特定 signature 研究，不适合支撑这句话

**优化后**：
> "Laryngeal cancer remains a significant clinical concern, with prognostic outcomes varying considerably across patients [PMID:39153653; PMID:40239580; PMID:41234877]. Late-stage disease is associated with increased morbidity and reduced survival, highlighting the importance of molecular risk stratification for clinical management [PMID:40239580]."

**改进**：
- 语气更稳妥："remains... clinical concern"（而非 "challenge with considerable burden"）
- 强调预后异质性："prognostic outcomes varying considerably"
- 引用更合适：综述 + 临床进展研究
- 第二句聚焦风险分层的必要性，而非简单重复疾病负担

---

### 第二段（研究现状）

**优化前**：
> "Transcriptomic profiling approaches have been applied to identify prognostic signatures in laryngeal cancer, with studies demonstrating the utility of differentially expressed genes in prognostic assessment [PMID:35910213; PMID:40229748; PMID:39085122]."

**问题**：
- "demonstrating the utility" 过于断言
- 引用包含机制研究（39085122: HOXA1-AKT/mTOR）

**优化后**：
> "Transcriptomic profiling approaches have been applied to identify molecular markers associated with patient prognosis in laryngeal cancer. Studies have employed differential expression analysis combined with survival modeling to screen for genes with prognostic significance [PMID:35910213; PMID:40239580]."

**改进**：
- 去掉 "demonstrating the utility"，改为更中性的 "have been applied"
- 明确方法："differential expression analysis combined with survival modeling"
- 引用更精准：两篇都是 DEG + survival modeling 研究
- 去掉机制研究引用

---

### 第三段（研究目标）

**优化前**：
> "We performed differential expression analysis using the edgeR package to establish a candidate gene pool, followed by univariate Cox regression analysis to evaluate the prognostic significance of the differentially expressed genes."

**问题**：
- 过于详细（提到 edgeR package）
- "evaluate the prognostic significance" 过于断言

**优化后**：
> "We performed differential expression analysis using the edgeR package to establish a candidate gene pool, followed by univariate Cox regression analysis to evaluate associations between gene expression and patient survival."

**改进**：
- 保留 edgeR（因为是本研究的核心方法）
- 改为更中性的 "evaluate associations"（而非 "evaluate significance"）
- 强调"关联"而非"意义"

---

## 五、语言优化总结

### 避免的表述

❌ "have demonstrated"
❌ "established"
❌ "revealed ... as"
❌ "significant clinical challenge with considerable morbidity and mortality burden"
❌ "the utility of"

### 推荐的表述

✅ "have been applied"
✅ "have been explored"
✅ "have employed"
✅ "may help identify"
✅ "are being investigated"
✅ "remains a significant clinical concern"
✅ "is associated with"
✅ "highlighting the importance of"

---

## 六、最终 PMID 使用情况

### 第一段（疾病背景）

**使用的 PMID**：
- 39153653 (Circular RNAs 综述)
- 40239580 (T/N 分期的分子特征)
- 41234877 (THBS1 预后标志物)

**为什么**：
- 都包含明确的疾病负担/临床重要性陈述
- 39153653 是综述，最适合作为背景引用
- 40239580 提供临床进展/分期相关的背景
- 41234877 提供疾病负担的直接陈述

### 第二段（研究现状）

**使用的 PMID**：
- 35910213 (免疫基因组学预后签名)
- 40239580 (T/N 分期的分子特征)

**为什么**：
- 35910213：典型的 DEG + Cox regression 研究，方法学完全匹配
- 40239580：转录组分析 + 生存标志物筛选，方法学匹配
- 两篇都不过度机制化，适合作为方法学背景

### 第三段（研究目标）

**使用的 PMID**：无（self-description）

---

## 七、被降级的 PMID

### PMID:40229748 (m6A-ferroptosis)
- **原标签**：disease_background, prognostic_biomarker, transcriptome, survival_analysis
- **新标签**：prognostic_biomarker_signature, mechanism_or_specific_gene
- **降级原因**：太特定（m6A-ferroptosis pathway, TFRC/RGS4/FTH1），不适合通用背景
- **不再用于**：第一段疾病背景、第二段研究现状

### PMID:39085122 (HOXA1-AKT/mTOR)
- **原标签**：disease_background, prognostic_biomarker, survival_analysis
- **新标签**：mechanism_or_specific_gene
- **降级原因**：纯机制研究，不适合任何背景陈述
- **不再用于**：任何 claim

### PMID:39893643 (CTSL-IL6-JAK-STAT3)
- **原标签**：disease_background, prognostic_biomarker, transcriptome
- **新标签**：mechanism_or_specific_gene
- **降级原因**：纯机制研究，不适合任何背景陈述
- **不再用于**：任何 claim

---

## 八、核心改进点

1. **文献标签更精准**：区分通用背景 vs 特定研究 vs 机制研究
2. **Claims 绑定更合理**：第一段用综述+临床研究，第二段用方法学匹配的研究
3. **引言语言更稳妥**：避免过强断言，使用更中性的表述
4. **引用更适配**：每个句子的引用都经过仔细匹配，不再出现"特定 signature 支撑通用背景"的问题

---

## 九、质量提升对比

| 维度 | 优化前 | 优化后 |
|------|--------|--------|
| 第一段引用质量 | 特定 signature 研究 | 综述 + 临床进展研究 |
| 第二段引用质量 | 包含机制研究 | 纯方法学匹配研究 |
| 语言断言强度 | "demonstrated", "established" | "have been applied", "may help" |
| 疾病背景适配性 | 中等 | 高 |
| 方法学背景适配性 | 中等 | 高 |
| 整体 SCI 写作质量 | 良好 | 优秀 |
