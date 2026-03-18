# SCIWriter 开发日志（Day 02）

日期：2026-03-17

## 一、今日开发目标

今日开发的核心目标，是在现有项目扫描、证据提取和 Results/Methods/Abstract 自动写作原型的基础上，继续完善手稿组装链路，并补充后续系统化开发所需的规则和规划文件。重点工作包括：

1. 完成 `write_title.py` 的设计与验证，生成标题候选。
2. 完成 `assemble_manuscript.py` 的设计与验证，将现有章节组装成完整手稿骨架。
3. 明确系统在疾病类型、研究切入点、人工背景说明方面不能仅依赖自动识别，需引入项目级人工 brief 输入层。
4. 将“结果与图优先、代码辅助”的原则进一步固化为系统级规范。
5. 明确后续开发路线，重点转向 `project_brief.yaml`、`write_intro.py` 和 `write_discussion.py`。

---

## 二、今日完成的开发内容

### 1. 完成 `write_title.py` 流程验证

今日已完成标题生成流程的原型验证。当前流程能够：

- 检查标题生成所需文件是否齐全；
- 基于 `project.yaml`、`storyline.md`、`abstract_draft.md`、`results_draft.md` 生成标题写作输入；
- 生成：
  - `title_manifest.json`
  - `title_prompt.txt`
- 由 Claude 基于标准化 prompt 生成 `title_candidates.md`。

当前示例项目中已生成 3 个英文标题候选，说明标题自动化链路已经初步打通。

### 2. 完成 `assemble_manuscript.py` 流程验证

今日已完成手稿组装脚本 `assemble_manuscript.py` 的原型验证。当前脚本能够：

- 检查 `abstract_draft.md`、`methods_draft.md`、`results_draft.md` 是否存在；
- 自动生成 `manuscript_v1.md`；
- 按顺序组装：
  - Title（占位）
  - Abstract
  - Methods
  - Results
  - Discussion（占位）
- 自动去除章节草稿中的重复一级标题；
- 在文稿顶部增加自动组装注释块，标注当前手稿完成状态。

这意味着 SCIWriter 已经不仅能生成单个章节草稿，而是能够组装出一份完整的手稿骨架。

### 3. 明确疾病与研究切入点不能完全依赖自动识别

在标题生成阶段暴露出一个关键问题：

- 系统当前无法仅凭项目目录、结果表和脚本稳定判断癌种；
- 系统也无法可靠识别“研究切入点”是否应进入标题或摘要；
- 例如：某个项目实际研究对象是喉癌，但文件中未明确写出疾病名称；
- 又例如：项目最初考虑“氮代谢相关基因”，但最终分析流程并未真正采用该切入点，若系统盲目从早期文件或主观意图推断，容易在标题、摘要、前言中写偏。

因此，今日明确形成一个新的系统设计原则：

**凡是自动扫描无法稳定识别，但又会显著影响标题、摘要、Introduction 和 Discussion 的信息，必须允许人工通过项目级 brief 文件进行补充。**

### 4. 明确引入 `project_brief.yaml` 的必要性

结合上述问题，今日提出后续必须新增一个项目级人工输入层：

- 文件建议名：`project_brief.yaml`
- 作用：补充疾病名称、研究主线、切入点、背景说明、避免误写的内容、优先强调的方向等。

该文件后续预计将影响：

- 标题生成
- 摘要生成
- Introduction 生成
- Discussion 生成
- 项目整体主线判断

### 5. 固化“结果与图优先、代码辅助”的系统原则

今日再次明确并加固了一条关键系统原则：

**最终写作必须以最终结果表和最终图为主证据，代码只能作为辅助方法来源，不能凌驾于最终结果之上。**

这条原则已被纳入规则文档，并将作为后续 Results、Methods、Introduction、Discussion 自动生成时的统一约束。

### 6. 完成 `writing_rules.md` 的规则落地

今日已将 SCIWriter 的核心证据优先级与写作约束进一步落实到规则文件中。当前规则已经明确：

- Results 以 `evidence.csv`、结果表和最终图为主证据；
- Methods 先由结果确认分析类型，再由代码补充实现细节；
- 不得编造数值；
- 不得让代码覆盖最终结果；
- 若代码与结果不一致，则必须采用保守写法；
- 自动生成内容必须遵守模块顺序和项目主线。

---

## 三、今日开发过程中的关键判断与设计更新

### 1. Methods 自动化不能单纯依赖代码

今日明确确认：

- 某些项目只有结果表和图片，没有代码；
- 某些项目虽然有代码，但可能并非最终版本；
- 某些项目代码保存不完整，但最终结果表和图是可靠的。

因此，Methods 自动化后续必须支持三种模式：

- `code_driven`
- `result_driven`
- `structure_driven`

也就是说，代码驱动只是其中一种模式，而不是唯一模式。

### 2. 标题、摘要、前言、讨论都需要“人工意图层”

今日开发中进一步确认：

Results 和 Methods 可以相对更多依赖自动识别与结构化证据；
但以下章节更依赖“研究者意图”：

- Title
- Abstract
- Introduction
- Discussion

因此，系统后续必须引入一个轻量、低负担、可人工填写的项目 brief 文件，以避免系统误判研究对象和切入点。

### 3. 系统后续不能只做“自动读文件”

当前已明确，SCIWriter 后续将采用：

- 自动识别层
- 结构化证据层
- 人工项目意图层

三者并行的方案，而不是单纯依赖文件自动扫描。

---

## 四、当前系统已达到的阶段

截至今日，SCIWriter 已经具备以下能力：

### 已完成模块
- `scan_project.py`
- `build_module_context.py`
- `build_evidence.py`
- `build_project_files.py`
- `run_pipeline.py`
- `write_results.py`
- `build_methods_context.py`
- `write_methods.py`
- `write_abstract.py`
- `assemble_manuscript.py`
- `write_title.py`（流程已验证）

### 已可自动生成内容
- `project_scan.json`
- `module_context.json`
- `methods_context.json`
- `evidence.csv`
- `project.yaml`
- `storyline.md`
- `results_draft.md`
- `methods_draft.md`
- `abstract_draft.md`
- `title_candidates.md`
- `manuscript_v1.md`

### 当前阶段判断
当前系统已不再是“单章节写作原型”，而是已经进入：

**多章节自动写作 + 手稿骨架组装阶段**

不过，整篇 SCI 自动化仍缺少：

- 项目级人工 brief 输入层
- Introduction 自动化
- Discussion 自动化
- Title 正式回填至手稿
- 后续整篇手稿统一润色与质控

---

## 五、后续开发计划（今日更新版）

### 第一优先级：新增 `project_brief.yaml` 机制

目标：
为每个项目提供一个轻量级人工说明入口，补充系统难以自动识别但又高度影响写作质量的信息。

建议字段包括：

- 疾病名称
- 疾病缩写
- 主研究主题
- 生物学切入点
- 人工背景说明
- 重点强调方向
- 避免误写的内容
- 标题风格偏好

该文件后续将优先接入：

- `write_title.py`
- `write_abstract.py`
- `write_intro.py`
- `write_discussion.py`

### 第二优先级：开发 `write_intro.py`

原因：
Introduction 对疾病信息、研究背景、切入点依赖最强，因此应在 `project_brief.yaml` 机制建立后再推进。

目标：
基于：
- `project_brief.yaml`
- `project.yaml`
- `storyline.md`
- `abstract_draft.md`
- `results_draft.md`

自动生成：
- `intro_manifest.json`
- `intro_prompt.txt`
- `introduction_draft.md`

### 第三优先级：开发 `write_discussion.py`

目标：
在已有 Results、Methods、Abstract、project brief 基础上，生成保守、证据一致的 Discussion 初稿。

重点要求：
- 不引入 Results 中未支持的数字
- 不把相关性写成机制
- 允许适度解释，但严格受控

### 第四优先级：将 Title 正式纳入 manuscript assembly

后续应支持：
- 从 `title_candidates.md` 中选择一个标题；
- 自动写回 `manuscript_v1.md`；
- 或升级 `assemble_manuscript.py` 支持读取 `title_selected.txt` / `title_final.md`。

### 第五优先级：后续再做统一整合

在 Title、Introduction、Discussion 都打通后，再考虑：

- 升级 `run_pipeline.py`
- 整合全流程
- 支持 `--with-results`、`--with-methods`、`--with-abstract` 等参数
- 最终支持一键从项目目录到整篇 manuscript

---

## 六、当前阶段结论

今日开发工作的核心成果不是单纯新增了一个标题生成脚本，而是明确了 SCIWriter 未来必须从“自动读取项目文件”进一步升级为：

**自动结构化 + 人工项目意图补充 + 分章节保守写作**

这意味着 SCIWriter 后续的正确发展方向已经进一步明确：

- Results/Methods 继续坚持证据驱动
- Introduction/Discussion/Title 逐步引入人工 brief
- 结果表和最终图仍然保持最高事实优先级
- 代码始终维持辅助地位

今日开发已将项目推进到一个新的阶段：

**从章节级自动写作原型，进入接近整篇 SCI 自动组装的过渡阶段。**
