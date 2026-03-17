# SCIWriter

SCIWriter 是一个面向生信分析结果的 SCI 文章自动写作原型工具。

它的核心思路不是让大模型直接去“猜”整个项目，而是先通过脚本自动整理项目目录、识别分析模块、提取关键证据，再把这些结构化结果交给 Claude 去生成 SCI 风格的写作内容。

目前这个项目还处在 **V1 原型阶段**，已经可以完成从项目目录到 Results 初稿的基本流程。

---

## 这个项目想解决什么问题

平时做生信项目时，一个项目目录里通常会有很多分析步骤，比如：

- 差异分析
- 单因素 Cox
- LASSO
- 多因素 Cox
- 富集分析
- 免疫浸润分析
- 单细胞分析

每个步骤下面又会有：

- 结果表
- 图片
- 代码
- 输入文件

如果直接让大模型去读整个目录，往往会出现：

- 读不全
- 乱猜
- 数值写错
- 不知道先写什么后写什么

SCIWriter 的目标就是把这件事标准化：

1. 先自动扫描项目目录  
2. 再识别每个模块是什么分析  
3. 再提取适合写作的关键证据  
4. 再自动生成项目主线  
5. 最后交给 Claude 去写文章内容  

---

## 当前已经完成的功能

目前已经完成的 V1 功能有：

### 1. 项目扫描
可以扫描一个项目目录，并识别一级分析模块文件夹。

### 2. 模块识别
当前已经支持识别：

- 差异表达分析（differential_expression）
- 单因素 Cox 分析（univariate_cox）

### 3. 模块上下文生成
可以为每个模块自动生成 `module_context.json`，包括：

- 模块类型
- 模块目标
- 关键结果文件
- 脚本文件
- 输入文本文件

### 4. 证据提取
可以为每个模块自动生成 `evidence.csv`，用于保存后续写作需要的关键证据。

### 5. 项目级文件生成
可以自动生成：

- `project.yaml`
- `storyline.md`

### 6. Results 初稿生成
基于上面的结构化文件，可以让 Claude 自动写出 SCI 风格的 Results 初稿。

---

## 当前仓库结构

```text
SCIWriter/
├── scripts/        # 自动化脚本
├── prompts/        # Claude 写作提示模板
├── templates/      # 后续规则模板库
├── examples/       # 示例项目
├── outputs/        # 输出结果
├── docs/           # 开发日志、说明文档
├── README.md
├── .gitignore
└── requirements.txt

## scripts 目录目前包含的脚本
scan_project.py

扫描项目目录，识别模块，并生成 project_scan.json

build_module_context.py

为每个模块生成 module_context.json

build_evidence.py

从结果表中提取关键证据，并生成 evidence.csv

build_project_files.py

生成项目级文件：

project.yaml

storyline.md

当前支持的项目流程

当前 V1 的基本流程是：

扫描项目目录

识别模块

生成模块上下文

提取证据

生成项目级配置和主线

调用 Claude 写 Results

示例项目

当前仓库中可以放一个示例项目，帮助测试和演示。

例如：

examples/claude_writing_test/
├── 01_DEGs/
│   ├── diffSig.xls
│   └── edgeR.R
└── 02_unicox/
    ├── Autophagy.uniCox.R
    ├── dandaixie.txt
    ├── diffSig.xls
    ├── sur_expr_allmRNA.txt
    └── uniCox.txt

这个示例项目当前已经用于测试：

项目扫描

模块识别

证据提取

Results 初稿生成

当前支持的分析类型

当前只支持两类分析：

differential_expression

univariate_cox

后续计划增加：

LASSO

multivariate Cox

ROC / nomogram

GO / KEGG / GSEA

immune infiltration

validation

single-cell / spatial transcriptomics

当前项目状态

当前阶段：V1 原型

已经完成：

项目扫描

模块识别

模块上下文生成

证据提取

项目级文件生成

Results 初稿生成

下一步计划：

增强 evidence 提取能力

增加更多分析类型支持

增加 run_pipeline.py

增加 Methods 自动生成

后续扩展到整篇文章自动写作

设计原则

这个项目的核心原则是：

1. 脚本负责结构化

脚本负责：

扫描目录

识别模块

提取证据

组织项目结构

2. Claude 负责写作表达

Claude 负责：

根据结构化结果写学术语言

生成 Results / Methods / Discussion 等章节

3. 不直接让 Claude 乱读整个项目目录

而是先由程序筛选和整理，再交给 Claude 写作。

这样做的目的是提高：

稳定性

可控性

可复用性

批量处理能力

依赖环境

当前最基础的 Python 依赖包括：

pandas

pyyaml

安装方式：

pip install -r requirements.txt
后续目标

最终目标不是只生成一段 Results，而是让系统能够：

读取完整项目目录

自动判断文章路线

自动组织章节结构

自动生成整篇 SCI 初稿，包括：

Title

Abstract

Introduction

Methods

Results

Discussion

Figure legends

说明

当前仓库仍然是开发中的原型版本，不是最终产品。

它更适合作为：

生信项目自动写作框架

规则库与模板库的开发基础

Claude 辅助科研写作流程的实验平台