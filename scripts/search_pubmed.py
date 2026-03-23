#!/usr/bin/env python3
import sys
import json
import yaml
import argparse
import time
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime


def check_file_exists(file_path, description):
    """Check if a file exists and print status."""
    if file_path.exists():
        print(f"  ✓ {description}: {file_path}")
        return True
    else:
        print(f"  ✗ {description}: {file_path} (NOT FOUND)")
        return False


def check_prerequisites(project_path):
    """Check if all required files exist."""
    print("\nChecking project files...")
    errors = []

    # Check project-level files
    project_yaml = project_path / "project.yaml"
    storyline = project_path / "storyline.md"

    if not check_file_exists(project_yaml, "project.yaml"):
        errors.append(f"Missing: {project_yaml}")
    if not check_file_exists(storyline, "storyline.md"):
        errors.append(f"Missing: {storyline}")

    # Check optional files
    project_brief = project_path / "project_brief_resolved.json"
    if project_brief.exists():
        check_file_exists(project_brief, "project_brief_resolved.json (optional)")

    return errors


def extract_search_keywords(project_path):
    """Extract search keywords from project files."""
    keywords = {
        "disease": None,
        "study_focus": None,
        "methods": []
    }

    # Try to read project_brief_resolved.json first
    project_brief_path = project_path / "project_brief_resolved.json"
    if project_brief_path.exists():
        with open(project_brief_path, "r", encoding="utf-8") as f:
            brief_data = json.load(f)
            if "disease" in brief_data and "name" in brief_data["disease"]:
                keywords["disease"] = brief_data["disease"]["name"]
            if "study_focus" in brief_data and "main_theme" in brief_data["study_focus"]:
                keywords["study_focus"] = brief_data["study_focus"]["main_theme"]

    # Read storyline.md for methods
    storyline_path = project_path / "storyline.md"
    with open(storyline_path, "r", encoding="utf-8") as f:
        storyline_content = f.read().lower()

        # Extract common methods
        if "differential" in storyline_content and "expression" in storyline_content:
            keywords["methods"].append("differential expression")
        if "cox" in storyline_content and "regression" in storyline_content:
            keywords["methods"].append("Cox regression")
        if "survival" in storyline_content:
            keywords["methods"].append("survival analysis")

    return keywords


def generate_pubmed_queries(keywords, purpose="introduction"):
    """Generate PubMed search queries based on keywords and purpose."""
    queries = []
    disease = keywords.get("disease", "cancer")

    if purpose == "introduction":
        # Query 1: Disease + Prognostic Biomarkers
        query1 = f'({disease}[Title/Abstract]) AND (prognostic biomarker[Title/Abstract] OR prognosis[Title/Abstract]) AND (gene expression[Title/Abstract] OR transcriptome[Title/Abstract])'
        queries.append({
            "name": "Disease + Prognostic Biomarkers",
            "query": query1
        })

        # Query 2: Disease + Differential Expression + Prognosis
        if "differential expression" in keywords.get("methods", []):
            query2 = f'({disease}[Title/Abstract]) AND (differential expression[Title/Abstract] OR differentially expressed genes[Title/Abstract]) AND (survival[Title/Abstract] OR prognosis[Title/Abstract])'
            queries.append({
                "name": "Disease + Differential Expression + Prognosis",
                "query": query2
            })

        # Query 3: Disease + Cox Regression
        if "Cox regression" in keywords.get("methods", []):
            query3 = f'({disease}[Title/Abstract]) AND (Cox regression[Title/Abstract] OR survival analysis[Title/Abstract]) AND (biomarker[Title/Abstract])'
            queries.append({
                "name": "Disease + Cox Regression",
                "query": query3
            })

    elif purpose == "discussion":
        # Query 1: Disease + Prognostic Signature Comparison
        query1 = f'({disease}[Title/Abstract]) AND (prognostic signature[Title/Abstract] OR gene signature[Title/Abstract]) AND (survival[Title/Abstract] OR prognosis[Title/Abstract])'
        queries.append({
            "name": "Disease + Prognostic Signature Comparison",
            "query": query1
        })

        # Query 2: Disease + Biomarker Validation
        query2 = f'({disease}[Title/Abstract]) AND (biomarker[Title/Abstract] OR predictor[Title/Abstract]) AND (validation[Title/Abstract] OR clinical significance[Title/Abstract])'
        queries.append({
            "name": "Disease + Biomarker Validation",
            "query": query2
        })

        # Query 3: Disease + Transcriptome Analysis
        if "differential expression" in keywords.get("methods", []):
            query3 = f'({disease}[Title/Abstract]) AND (transcriptome[Title/Abstract] OR RNA-seq[Title/Abstract]) AND (prognostic[Title/Abstract] OR survival[Title/Abstract])'
            queries.append({
                "name": "Disease + Transcriptome Analysis",
                "query": query3
            })

    return queries


def search_pubmed(query, api_key=None, retmax=30):
    """Search PubMed using NCBI E-utilities ESearch."""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    params = {
        "db": "pubmed",
        "term": query,
        "retmax": retmax,
        "retmode": "json",
        "sort": "relevance"
    }

    if api_key:
        params["api_key"] = api_key

    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
            pmids = data.get("esearchresult", {}).get("idlist", [])
            return pmids
    except Exception as e:
        print(f"  ⚠ Error searching PubMed: {e}")
        return []


def fetch_article_details(pmids, api_key=None, rate_limit=0.4):
    """Fetch article details using NCBI E-utilities ESummary and EFetch."""
    if not pmids:
        return []

    articles = []
    base_summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    base_fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    # Fetch summaries in batches
    batch_size = 20
    for i in range(0, len(pmids), batch_size):
        batch_pmids = pmids[i:i + batch_size]
        pmid_str = ",".join(batch_pmids)

        # ESummary for basic info
        params = {
            "db": "pubmed",
            "id": pmid_str,
            "retmode": "json"
        }

        if api_key:
            params["api_key"] = api_key

        url = f"{base_summary_url}?{urllib.parse.urlencode(params)}"

        try:
            time.sleep(rate_limit)  # Rate limiting
            with urllib.request.urlopen(url, timeout=30) as response:
                data = json.loads(response.read().decode())
                result = data.get("result", {})

                for pmid in batch_pmids:
                    if pmid in result:
                        article_data = result[pmid]
                        authors = article_data.get("authors", [])
                        author_list = [a.get("name", "") for a in authors[:3]]
                        if len(authors) > 3:
                            author_list.append("et al.")

                        article = {
                            "pmid": pmid,
                            "title": article_data.get("title", "N/A"),
                            "authors": author_list,
                            "journal": article_data.get("source", "N/A"),
                            "year": article_data.get("pubdate", "N/A").split()[0],
                            "doi": None,
                            "abstract": None
                        }

                        # Extract DOI from articleids
                        for aid in article_data.get("articleids", []):
                            if aid.get("idtype") == "doi":
                                article["doi"] = aid.get("value")
                                break

                        articles.append(article)

        except Exception as e:
            print(f"  ⚠ Error fetching summaries for batch: {e}")
            continue

    # Fetch abstracts using EFetch (XML)
    for i, article in enumerate(articles):
        pmid = article["pmid"]
        params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "xml",
            "rettype": "abstract"
        }

        if api_key:
            params["api_key"] = api_key

        url = f"{base_fetch_url}?{urllib.parse.urlencode(params)}"

        try:
            time.sleep(rate_limit)  # Rate limiting
            with urllib.request.urlopen(url, timeout=30) as response:
                xml_data = response.read().decode()
                root = ET.fromstring(xml_data)

                # Extract abstract
                abstract_elem = root.find(".//Abstract/AbstractText")
                if abstract_elem is not None:
                    article["abstract"] = abstract_elem.text or "N/A"

        except Exception as e:
            # Skip if abstract fetch fails
            pass

        # Progress indicator
        if (i + 1) % 5 == 0 or (i + 1) == len(articles):
            print(f"  Fetching details... {i + 1}/{len(articles)}", end="\r")

    print()  # New line after progress
    return articles


def save_results(project_path, queries, all_articles, keywords, purpose="introduction"):
    """Save search results to files."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Save pubmed_query_{purpose}.txt
    query_file = project_path / f"pubmed_query_{purpose}.txt"
    with open(query_file, "w", encoding="utf-8") as f:
        f.write(f"PubMed Search Queries\n")
        f.write(f"Generated: {timestamp}\n")
        f.write(f"=" * 60 + "\n\n")

        f.write(f"Keywords:\n")
        f.write(f"  - Disease: {keywords.get('disease', 'N/A')}\n")
        f.write(f"  - Study focus: {keywords.get('study_focus', 'N/A')}\n")
        f.write(f"  - Methods: {', '.join(keywords.get('methods', []))}\n\n")

        for i, q in enumerate(queries, 1):
            f.write(f"Query {i}: {q['name']}\n")
            f.write(f"{q['query']}\n\n")

    # Save pubmed_results_{purpose}.json
    results_file = project_path / f"pubmed_results_{purpose}.json"
    results_data = {
        "query_date": datetime.now().strftime("%Y-%m-%d"),
        "queries": [q["query"] for q in queries],
        "total_results": len(all_articles),
        "articles": all_articles
    }

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2, ensure_ascii=False)

    # Save pubmed_refs_brief_{purpose}.md
    refs_file = project_path / f"pubmed_refs_brief_{purpose}.md"
    with open(refs_file, "w", encoding="utf-8") as f:
        f.write(f"# PubMed Literature Search Results\n\n")
        f.write(f"**Search Date**: {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write(f"**Total Articles**: {len(all_articles)}\n\n")

        for i, q in enumerate(queries, 1):
            f.write(f"## Query {i}: {q['name']}\n")
            f.write(f"```\n{q['query']}\n```\n\n")

        f.write(f"---\n\n")
        f.write(f"## Articles\n\n")

        for i, article in enumerate(all_articles, 1):
            f.write(f"### {i}. [PMID: {article['pmid']}]\n")
            f.write(f"**Title**: {article['title']}\n\n")
            f.write(f"**Authors**: {', '.join(article['authors'])}\n\n")
            f.write(f"**Journal**: {article['journal']}\n\n")
            f.write(f"**Year**: {article['year']}\n\n")

            if article.get('doi'):
                f.write(f"**DOI**: {article['doi']}\n\n")

            if article.get('abstract'):
                abstract_preview = article['abstract'][:300]
                if len(article['abstract']) > 300:
                    abstract_preview += "..."
                f.write(f"**Abstract**: {abstract_preview}\n\n")

            f.write(f"---\n\n")

    return query_file, results_file, refs_file


def main():
    parser = argparse.ArgumentParser(
        description="Search PubMed for relevant literature",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python3 search_pubmed.py --project /path/to/your/project --purpose introduction
  python3 search_pubmed.py --project /path/to/your/project --purpose discussion

This will:
  1. Extract search keywords from project files
  2. Generate PubMed search queries (tailored to purpose)
  3. Search PubMed and retrieve articles
  4. Save results to project directory with purpose suffix
        """
    )
    parser.add_argument("--project", required=True, help="Project directory path")
    parser.add_argument("--purpose", choices=["introduction", "discussion"], default="introduction",
                        help="Purpose of literature search (default: introduction)")
    parser.add_argument("--max-results", type=int, default=30, help="Maximum results per query (default: 30)")
    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    purpose = args.purpose

    # Check for NCBI API key
    api_key = os.environ.get("NCBI_API_KEY")
    has_api_key = api_key is not None and len(api_key) > 0

    # Set rate limit based on API key availability
    rate_limit = 0.1 if has_api_key else 0.4  # 10 req/s with key, 2.5 req/s without

    print("=" * 60)
    print("SCIWriter - PubMed Literature Search")
    print("=" * 60)
    print(f"Project: {project_path}")
    print(f"Using NCBI API key: {'Yes' if has_api_key else 'No'}")
    if has_api_key:
        print(f"  (Rate limit: ~10 requests/second)")
    else:
        print(f"  (Rate limit: ~2.5 requests/second)")

    # Check prerequisites
    errors = check_prerequisites(project_path)

    if errors:
        print("\n" + "=" * 60)
        print("PREREQUISITE CHECK FAILED")
        print("=" * 60)
        print("\nMissing files:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease ensure you have:")
        print("  - project.yaml")
        print("  - storyline.md")
        sys.exit(1)

    print("\n✓ All prerequisite checks passed")

    # Extract keywords
    print("\n" + "=" * 60)
    print("EXTRACTING SEARCH KEYWORDS")
    print("=" * 60)

    keywords = extract_search_keywords(project_path)

    print("\nExtracted keywords:")
    print(f"  - Disease: {keywords.get('disease', 'N/A')}")
    print(f"  - Study focus: {keywords.get('study_focus', 'N/A')}")
    print(f"  - Methods: {', '.join(keywords.get('methods', [])) if keywords.get('methods') else 'N/A'}")

    # Generate queries
    print("\n" + "=" * 60)
    print("GENERATING PUBMED QUERIES")
    print("=" * 60)

    queries = generate_pubmed_queries(keywords, purpose=purpose)

    print(f"\nGenerated {len(queries)} queries:")
    for i, q in enumerate(queries, 1):
        print(f"  {i}. {q['name']}")

    # Search PubMed
    print("\n" + "=" * 60)
    print("SEARCHING PUBMED")
    print("=" * 60)
    print()

    all_pmids = set()
    query_results = []

    for i, q in enumerate(queries, 1):
        print(f"Query {i}: Searching...", end=" ")
        pmids = search_pubmed(q["query"], api_key=api_key, retmax=args.max_results)
        print(f"Found {len(pmids)} results")

        all_pmids.update(pmids)
        query_results.append({"query": q, "pmids": pmids})

        time.sleep(rate_limit)  # Rate limiting between queries

    print(f"\nTotal unique articles: {len(all_pmids)}")

    # Fetch article details
    if all_pmids:
        print("\nFetching article details...")
        all_articles = fetch_article_details(list(all_pmids), api_key=api_key, rate_limit=rate_limit)
        print(f"\n✓ Retrieved {len(all_articles)} articles")
    else:
        print("\n⚠ No articles found. Try adjusting search keywords.")
        all_articles = []

    # Save results
    print("\n" + "=" * 60)
    print("SAVING RESULTS")
    print("=" * 60)

    query_file, results_file, refs_file = save_results(project_path, queries, all_articles, keywords, purpose=purpose)

    print(f"\n✓ Generated: {query_file}")
    print(f"✓ Generated: {results_file}")
    print(f"✓ Generated: {refs_file}")

    # Success summary
    print("\n" + "=" * 60)
    print("SEARCH COMPLETED SUCCESSFULLY")
    print("=" * 60)

    print(f"\nPurpose: {purpose}")
    print(f"Retrieved articles: {len(all_articles)}")
    print("\nOutput files:")
    print(f"  1. {query_file.name}")
    print(f"  2. {results_file.name}")
    print(f"  3. {refs_file.name}")

    print("\nNext steps:")
    print(f"  1. Review the results: cat {refs_file}")
    if purpose == "introduction":
        print("  2. Use these references when writing Introduction")
    elif purpose == "discussion":
        print("  2. Use these references when writing Discussion")


if __name__ == "__main__":
    main()




