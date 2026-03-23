You are generating a Discussion section for a biomedical SCI manuscript.

Requirements:
- Use formal academic English.
- Base the discussion on the provided project information, abstract, results, and introduction.
- Structure: main findings → interpretation → value → limitations & conclusion.
- Do not exaggerate novelty or significance.
- Do not claim mechanisms unless clearly supported.
- Avoid "novel mechanism", "breakthrough", "therapeutic target", "clinical application", "revolutionary", "paradigm shift".
- Keep the tone conservative and objective.
- Suitable for transcriptomic/bioinformatics biomarker studies.
- Do not fabricate citations (use placeholder [ref] if needed).
- Focus on "candidate", "potential", "warrant further investigation", "may suggest".
- Must include a limitations paragraph with: retrospective public-data-based analysis, lack of independent cohort validation, lack of experimental validation.
- The discussion should be exactly 4 paragraphs, 900–1200 words total.

**Gene mention rules (apply to all paragraphs):**
- Do NOT enumerate individual gene names or functions one by one.
- Mention at most 2–3 representative genes by name, only when directly supported by the results.
- Do NOT write mechanistic interpretations for individual genes (e.g., "may reflect aggressive metabolism", "plays a role in tumor progression") unless the current study's evidence or a cited reference explicitly supports it.
- Focus on patterns, directions (risk/protective), and the overall screening outcome — not gene-by-gene biology.

Paragraph-specific requirements:

**Paragraph 1 (Main findings overview):**
- Open with the study's analytical approach and overall outcome — NOT a restatement of specific numbers from Results or Abstract.
- Do NOT repeat exact counts (e.g., "4774 DEGs", "16 candidates", "9 genes") unless they are essential context.
- Do NOT write this paragraph as a Results summary or Abstract paraphrase.
- Write like a Discussion opening: frame what was done and what the outcome means at a high level.
- Limit gene-name mentions to 1–2 at most; do not explain their individual biology here.

**Paragraph 2 (Literature comparison):**
- Must explicitly reflect the study's analytical pathway: differential expression analysis → univariate Cox regression.
- Compare findings to existing literature using PMID citations in format [PMID:12345678].
- Paragraph 2 should have the highest citation density in the Discussion.
- Emphasize consistency or comparability with prior work — avoid overclaiming differences.
- Do NOT make strong biological inferences beyond what the cited papers support.
- Do NOT use only generic phrases like "is consistent with previous investigations" or "provides a framework".

**Paragraph 3 (Methodological value):**
- Explain specifically why the DEG → survival analysis pathway is a reasonable strategy for candidate prognostic gene discovery.
- Discuss the value of systematic screening methods in this context.
- Do NOT only say "future validation" or "potential application" without substance.
- Remain conservative but be specific about methodological value.
- May include 1–2 methodological citations if available.

**Paragraph 4 (Limitations & conclusion):**
- Must include these four specific limitations:
  1. Retrospective public-data-based analysis
  2. Lack of independent cohort validation
  3. Lack of experimental validation
  4. Univariate Cox regression does not account for clinical confounders (multivariate analysis needed)
- Conclude conservatively, aligning with the study title and objectives.

Avoid generic/template phrases:
- "is consistent with previous investigations"
- "provides a framework"
- "providing a foundation for future validation studies"
- "similar studies have shown"
- "these findings suggest that"
- "may reflect aggressive metabolism"
- "plays a role in tumor progression"

Use more specific, study-relevant language instead.
