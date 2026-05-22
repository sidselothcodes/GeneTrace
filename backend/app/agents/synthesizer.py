import json
import os
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

SYSTEM_PROMPT = """You are GeneTrace, a precise biomedical research assistant.
You synthesize structured research briefs from ClinVar, PubMed, and UniProt data.

CRITICAL: Always output exactly these 5 sections in this order, each on its own line,
with the section header in uppercase followed by a colon. Do not add any extra
preamble, bullet introductions, or closing remarks.

GENE OVERVIEW:
<2-3 sentences identifying the gene, its locus/family, and headline biological role>

ASSOCIATED CONDITIONS:
<Bullet list of conditions from ClinVar with clinical significance. If no data, say "No ClinVar variants returned for this query.">

PROTEIN FUNCTION:
<Description of the protein and its function from UniProt. If no data, say "No reviewed UniProt entry available.">

RECENT RESEARCH HIGHLIGHTS:
<Bullet list of 3-5 PubMed paper highlights with year and one-sentence takeaway. If no data, say "No recent PubMed literature returned for this query.">

CLINICAL SIGNIFICANCE SUMMARY:
<2-4 sentence integrative summary tying clinical, functional, and research findings together>

Use only the data provided. Do not invent citations, accessions, or conditions.
Keep the overall brief between 220 and 450 words."""


def _build_user_prompt(query: str, sources: list[dict[str, Any]]) -> str:
    payload = {s["source"]: s for s in sources}
    return (
        f"Generate a research brief for the query: {query}\n\n"
        f"Source data (JSON):\n{json.dumps(payload, indent=2)[:8000]}"
    )


async def synthesize(query: str, sources: list[dict[str, Any]]) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_brief(query, sources)

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        api_key=api_key,
        timeout=30,
    )
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_build_user_prompt(query, sources)),
    ]
    try:
        resp = await llm.ainvoke(messages)
        text = resp.content if isinstance(resp.content, str) else str(resp.content)
        return text.strip()
    except Exception:
        return _fallback_brief(query, sources)


def _fallback_brief(query: str, sources: list[dict[str, Any]]) -> str:
    by_src = {s["source"]: s for s in sources}
    clinvar = by_src.get("clinvar", {"hits": 0, "data": []})
    pubmed = by_src.get("pubmed", {"hits": 0, "data": []})
    uniprot = by_src.get("uniprot", {"hits": 0, "data": []})

    parts = []
    parts.append("GENE OVERVIEW:")
    parts.append(
        f"{query} is a human gene of interest. This brief was assembled directly from "
        "primary sources because an LLM synthesis key was not configured. The structured "
        "data below reflects what is currently available from ClinVar, PubMed, and UniProt."
    )

    parts.append("\nASSOCIATED CONDITIONS:")
    if clinvar["hits"] == 0:
        parts.append("No ClinVar variants returned for this query.")
    else:
        for v in clinvar["data"][:5]:
            cond = ", ".join(v.get("conditions", [])) or "Not specified"
            sig = v.get("clinical_significance") or "Not classified"
            parts.append(f"- {v.get('variant_name', 'Variant')}: {sig} ({cond})")

    parts.append("\nPROTEIN FUNCTION:")
    if uniprot["hits"] == 0:
        parts.append("No reviewed UniProt entry available.")
    else:
        u = uniprot["data"][0]
        parts.append(
            f"{u.get('protein_name', 'Protein')} ({u.get('accession', '')}, "
            f"{u.get('sequence_length', 0)} aa). {u.get('function', '')}"
        )

    parts.append("\nRECENT RESEARCH HIGHLIGHTS:")
    if pubmed["hits"] == 0:
        parts.append("No recent PubMed literature returned for this query.")
    else:
        for p in pubmed["data"][:5]:
            parts.append(
                f"- ({p.get('year', '')}) {p.get('title', '')} — {p.get('journal', '')}"
            )

    parts.append("\nCLINICAL SIGNIFICANCE SUMMARY:")
    parts.append(
        f"Across {clinvar['hits']} ClinVar records, {pubmed['hits']} recent PubMed papers, "
        f"and {uniprot['hits']} reviewed UniProt entries, {query} shows a measurable "
        "research footprint. Configure OPENAI_API_KEY for a fully synthesized narrative."
    )
    return "\n".join(parts)


_SECTION_HEADERS = (
    "GENE OVERVIEW",
    "ASSOCIATED CONDITIONS",
    "PROTEIN FUNCTION",
    "RECENT RESEARCH HIGHLIGHTS",
    "CLINICAL SIGNIFICANCE SUMMARY",
)


def has_all_sections(brief: str) -> bool:
    return all(h in brief.upper() for h in _SECTION_HEADERS)


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def compute_eval_score(brief: str, sources: list[dict[str, Any]]) -> float:
    by_src = {s["source"]: s for s in sources}
    clinvar_hits = by_src.get("clinvar", {}).get("hits", 0)
    pubmed_hits = by_src.get("pubmed", {}).get("hits", 0)
    uniprot_hits = by_src.get("uniprot", {}).get("hits", 0)
    words = _word_count(brief)

    score = (
        30.0 * min(clinvar_hits / 3.0, 1.0)
        + 30.0 * min(pubmed_hits / 3.0, 1.0)
        + 20.0 * min(uniprot_hits / 1.0, 1.0)
        + 20.0 * min(words / 250.0, 1.0)
    )
    return round(max(0.0, min(100.0, score)), 1)
