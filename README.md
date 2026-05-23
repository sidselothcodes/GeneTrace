# GeneTrace

> An agentic biomedical research tool that turns a gene name or variant into a structured research brief — pulling from ClinVar, PubMed, and UniProt in parallel, synthesizing with GPT-4o-mini, and persisting every trace to PostgreSQL.

---

## What it does

Enter a gene symbol (`BRCA2`), receptor (`EGFR`), or variant id (`rs334`) and GeneTrace will:

1. **Fan out in parallel** to three public biomedical APIs (ClinVar, PubMed, UniProt) via `asyncio.gather`.
2. **Synthesize a structured brief** with an LLM (LangChain + GPT-4o-mini) covering: gene overview, associated conditions, protein function, recent research highlights, and a clinical significance summary.
3. **Score data completeness** transparently on a 0–100 rubric (hit counts + brief length).
4. **Persist every trace** to PostgreSQL and expose a recent-history sidebar.

## Project Link

https://gene-trace.vercel.app/



