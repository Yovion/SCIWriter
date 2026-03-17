#!/usr/bin/env python3
import json
import argparse
import pandas as pd
from pathlib import Path


def try_read_table(file_path):
    """Try to read table with multiple separators."""
    for sep in ["\t", ","]:
        try:
            df = pd.read_csv(file_path, sep=sep)
            if len(df.columns) > 1:  # Valid table should have multiple columns
                return df
        except:
            continue
    return None


def find_column(df, possible_names):
    """Find column by trying multiple possible names (case-insensitive)."""
    df_columns_lower = {col.lower(): col for col in df.columns}
    for name in possible_names:
        if name.lower() in df_columns_lower:
            return df_columns_lower[name.lower()]
    return None


def extract_top_genes(df, gene_col, n=5):
    """Extract top N genes as semicolon-separated string."""
    if gene_col and gene_col in df.columns:
        genes = df[gene_col].head(n).astype(str).tolist()
        return ";".join(genes)
    return ""


def process_differential_expression(module_dir, key_result_file):
    """Process differential expression module."""
    file_path = module_dir / key_result_file

    if not file_path.exists():
        return None

    df = try_read_table(file_path)
    if df is None:
        return None

    evidence = {}

    # Find columns
    gene_col = find_column(df, ["gene", "symbol", "id"])
    logfc_col = find_column(df, ["logfc", "log2fc", "fc"])
    pval_col = find_column(df, ["adj.p.val", "fdr", "padj", "adj_p", "pvalue", "p.value"])

    # Basic statistics
    evidence["total_genes"] = len(df)

    # LogFC statistics
    if logfc_col:
        evidence["upregulated_count"] = int((df[logfc_col] > 0).sum())
        evidence["downregulated_count"] = int((df[logfc_col] < 0).sum())

    # Extract representative genes
    evidence["representative_genes"] = extract_top_genes(df, gene_col, n=5)

    return evidence


def process_univariate_cox(module_dir, key_result_file):
    """Process univariate Cox module."""
    file_path = module_dir / key_result_file

    if not file_path.exists():
        return None

    df = try_read_table(file_path)
    if df is None:
        return None

    evidence = {}

    # Find columns
    gene_col = find_column(df, ["gene", "symbol", "id"])
    hr_col = find_column(df, ["hr", "hazard_ratio", "hazardratio", "exp(coef)"])
    pval_col = find_column(df, ["pvalue", "p", "pr(>|z|)", "p.value"])

    # Basic statistics
    evidence["total_genes"] = len(df)

    # HR statistics
    if hr_col:
        evidence["risk_gene_count"] = int((df[hr_col] > 1).sum())
        evidence["protective_gene_count"] = int((df[hr_col] < 1).sum())

    # P-value statistics
    if pval_col:
        evidence["significant_gene_count"] = int((df[pval_col] < 0.05).sum())

    # Extract representative genes
    evidence["representative_genes"] = extract_top_genes(df, gene_col, n=5)

    return evidence


def build_evidence(project_scan_path):
    """Build evidence.csv for each module."""
    project_scan_path = Path(project_scan_path)

    # Read project scan
    with open(project_scan_path, "r", encoding="utf-8") as f:
        project_data = json.load(f)

    project_path = Path(project_data["project_path"])
    modules = project_data["modules"]

    print(f"Building evidence for {len(modules)} modules...\n")

    for module in modules:
        module_name = module["module_name"]
        module_type = module["module_type"]
        module_dir = project_path / module_name

        # Read module context
        context_path = module_dir / "module_context.json"
        if not context_path.exists():
            print(f"⚠ {module_name}: module_context.json not found, skipping")
            continue

        with open(context_path, "r", encoding="utf-8") as f:
            module_context = json.load(f)

        # Get key result file
        key_result_tables = module_context.get("key_result_tables", [])
        if not key_result_tables:
            print(f"⚠ {module_name}: no key_result_tables found, skipping")
            continue

        key_result_file = key_result_tables[0]

        # Process based on module type
        evidence = None
        if module_type == "differential_expression":
            evidence = process_differential_expression(module_dir, key_result_file)
        elif module_type == "univariate_cox":
            evidence = process_univariate_cox(module_dir, key_result_file)
        else:
            print(f"⚠ {module_name}: unsupported module type '{module_type}', skipping")
            continue

        if evidence is None:
            print(f"✗ {module_name}: failed to process {key_result_file}")
            continue

        # Save evidence.csv
        evidence_path = module_dir / "evidence.csv"
        evidence_df = pd.DataFrame(list(evidence.items()), columns=["item", "value"])
        evidence_df.to_csv(evidence_path, index=False)

        print(f"✓ {module_name}/evidence.csv")
        print(f"  Source: {key_result_file}")
        print(f"  Items: {len(evidence)}")
        for item, value in evidence.items():
            if item != "representative_genes":
                print(f"    {item}: {value}")
        print()

    print("Evidence generation completed!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build evidence.csv for each module")
    parser.add_argument("--project", required=True, help="Project directory path")
    args = parser.parse_args()

    project_scan_path = Path(args.project) / "project_scan.json"
    build_evidence(project_scan_path)
