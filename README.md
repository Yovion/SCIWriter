# SCIWriter Development Notes

## Project purpose
SCIWriter is a modular manuscript-generation pipeline for bioinformatics projects.

Its goal is to convert structured project outputs into a complete manuscript draft through a reproducible workflow.

The current system already supports:
- run_pipeline.py
- resolve_project_brief.py
- run_full_manuscript.py
- write_methods.py
- write_results.py
- write_abstract.py
- write_title.py
- write_introduction.py
- write_discussion.py
- assemble_manuscript.py

The pipeline can now produce a full manuscript draft containing:
- Title
- Abstract
- Introduction
- Methods
- Results
- Discussion

## Current workflow
1. run_pipeline.py
2. resolve_project_brief.py
3. search_pubmed.py --purpose introduction
4. build_methods_context.py
5. write_methods.py --execute
6. write_results.py --execute
7. write_abstract.py --execute
8. write_title.py --execute
9. write_introduction.py
10. search_pubmed.py --purpose discussion
11. write_discussion.py
12. assemble_manuscript.py

## Brief is mandatory
Project brief is a required input for cold-start projects.

Supported inputs:
- --user-brief "..."
- --user-brief-file /path/to/file

The full-manuscript runner must not continue without a brief.

## Output behavior
Generated draft files should overwrite previous versions by default.

Typical outputs include:
- project_brief_resolved.json
- methods_draft.md
- results_draft.md
- abstract_draft.md
- title_candidates.md or selected_title.txt
- introduction_draft.md
- discussion_draft.md
- manuscript_v1.md

## Current development focus
The current priority is no longer the DEG + univariate Cox two-module test path.

The current development focus is:
1. real multi-module project support
2. scan_project.py module recognition upgrade
3. build_evidence.py multi-module evidence extraction
4. write_results.py multi-module section generation
5. write_methods.py multi-module section generation

## Real-project adaptation rules
Real projects may contain:
- useful structured result files
- scripts
- figures
- noisy files
- mixed module directories

The code should adapt to the real project layout.
Do not rely on manually renaming or manually reorganizing project folders.

## Development constraints
- Prefer minimal modifications
- Handle one functional block per iteration
- Do not modify unrelated scripts in the same round
- Do not modify real project directory structure as a workaround
- Improve code so the pipeline adapts to the project, not the reverse

## Multi-module direction
SCIWriter is moving toward real multi-module project support.

Current target module families include:
- prognostic_model_training
- model_validation
- independent_prognostic_analysis
- nomogram_dca
- immune_infiltration
- immunotherapy_response
- functional_enrichment
- somatic_mutation_analysis
- drug_sensitivity_prediction
- clinical_correlation
- network_support
- visualization_support
