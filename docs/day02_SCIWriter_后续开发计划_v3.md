# SCIWriter 后续开发计划（V3）

## 一、当前已完成模块

- scan_project.py
- build_module_context.py
- build_evidence.py
- build_project_files.py
- run_pipeline.py
- write_results.py
- build_methods_context.py
- write_methods.py
- write_abstract.py
- assemble_manuscript.py
- write_title.py（流程已验证）

## 二、当前系统已具备的能力

### 1. 结构化预处理
- 项目扫描
- 模块识别
- module_context 生成
- evidence 提取
- project.yaml 生成
- storyline.md 生成

### 2. 章节写作准备
- Results 写作准备
- Methods 写作准备
- Abstract 写作准备
- Title 写作准备

### 3. 手稿组装
- 自动组装出 manuscript_v1.md
- 自动保留未完成章节占位

## 三、当前核心设计原则

1. 程序负责结构化，Claude 负责写作表达。
2. 最终写作以结果表和最终图为主证据，代码只作为辅助方法来源。
3. Results 不得编造数值。
4. Methods 不得盲信代码，若代码与结果不一致则采用保守写法。
5. 所有脚本必须通过 `--project` 接收项目路径。
6. 所有新模块必须保持简单、清晰、易修改。
7. 未来系统必须支持“有代码”和“无代码”两种项目输入模式。
8. 标题、摘要、前言、讨论等高层章节，必须允许人工补充项目背景和主线意图。

## 四、后续开发优先级

### 优先级 1：引入 `project_brief.yaml`

目标：
补充系统自动扫描难以稳定获取的关键信息。

建议字段：
- disease.name
- disease.abbreviation
- study_focus.main_theme
- biological_focus
- important_background
- avoid_overstatement
- preferred_emphasis
- writing_preferences

作用范围：
- 标题
- 摘要
- Introduction
- Discussion
- 项目整体主线判断

### 优先级 2：开发 `write_intro.py`

输入建议：
- project.yaml
- project_brief.yaml
- storyline.md
- abstract_draft.md
- results_draft.md
- title_candidates.md（可选）

输出建议：
- intro_manifest.json
- intro_prompt.txt
- introduction_draft.md

目标：
生成保守、结构清晰、基于背景和主线的 Introduction 初稿。

### 优先级 3：开发 `write_discussion.py`

输入建议：
- project_brief.yaml
- abstract_draft.md
- methods_draft.md
- results_draft.md
- manuscript_v1.md（可选）

输出建议：
- discussion_manifest.json
- discussion_prompt.txt
- discussion_draft.md

目标：
生成证据一致、不过度机制化、符合 SCI 风格的 Discussion 初稿。

### 优先级 4：标题正式回填

建议方式：
- 新增 `title_final.md` 或 `title_selected.txt`
- 升级 `assemble_manuscript.py` 支持正式标题回填

### 优先级 5：升级 manuscript assembly

在 Introduction 和 Discussion 完成后，升级组装脚本支持：
- Title
- Abstract
- Introduction
- Methods
- Results
- Discussion

并自动生成更完整的 manuscript_v2.md。

### 优先级 6：最后做统一总控整合

在各章节模块成熟后，再考虑：
- 升级 `run_pipeline.py`
- 支持 `--with-results`
- 支持 `--with-methods`
- 支持 `--with-abstract`
- 支持 `--with-intro`
- 支持 `--with-discussion`

## 五、建议新增文件

### 模板/规则层
- templates/project_brief_template.yaml
- prompts/intro_writer.md
- prompts/discussion_writer.md
- prompts/title_writer.md（已存在）

### 项目输入层
- project_brief.yaml

### 新的上下文/写作层
- write_intro.py
- write_discussion.py

## 六、当前阶段开发目标总结

当前阶段的目标已经从“做一个能写 Results 的工具”升级为：

**构建一个由结构化证据驱动、可逐步扩展到整篇 SCI 手稿自动生成的模块化写作系统。**

下一阶段的关键不是继续堆脚本，而是：

1. 建立人工意图补充层（project_brief）
2. 优先补足 Introduction 和 Discussion
3. 再完成整篇 manuscript 的闭环
