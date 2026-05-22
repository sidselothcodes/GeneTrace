import asyncio
import os
import re
from typing import Any
from xml.etree import ElementTree as ET

import httpx

TIMEOUT = 10.0
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
UNIPROT = "https://rest.uniprot.org/uniprotkb/search"

NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")


def _ncbi_params(**kwargs) -> dict:
    params = {"tool": "genetrace", "email": "seloth.sid@gmail.com"}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    params.update(kwargs)
    return params


async def _ncbi_get(client: httpx.AsyncClient, url: str, params: dict) -> httpx.Response:
    for attempt in range(3):
        resp = await client.get(url, params=params, timeout=TIMEOUT)
        if resp.status_code == 429:
            await asyncio.sleep(1.0 * (attempt + 1))
            continue
        return resp
    return resp


def _empty(source: str, error: str | None = None) -> dict[str, Any]:
    return {"source": source, "hits": 0, "data": [], "error": error}


async def fetch_clinvar(client: httpx.AsyncClient, query: str) -> dict[str, Any]:
    try:
        search_url = f"{EUTILS}/esearch.fcgi"
        search_resp = await _ncbi_get(
            client,
            search_url,
            _ncbi_params(
                db="clinvar",
                term=f"{query}[gene]",
                retmode="json",
                retmax=5,
            ),
        )
        search_resp.raise_for_status()
        ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return _empty("clinvar")

        summary_url = f"{EUTILS}/esummary.fcgi"
        summary_resp = await _ncbi_get(
            client,
            summary_url,
            _ncbi_params(db="clinvar", id=",".join(ids), retmode="json"),
        )
        summary_resp.raise_for_status()
        result = summary_resp.json().get("result", {})

        variants: list[dict[str, Any]] = []
        for uid in ids:
            item = result.get(uid)
            if not item:
                continue
            germline = item.get("germline_classification", {}) or {}
            trait_set = germline.get("trait_set", []) or []
            conditions = [t.get("trait_name") for t in trait_set if t.get("trait_name")]
            variants.append(
                {
                    "id": uid,
                    "variant_name": item.get("title") or item.get("variation_set", [{}])[0].get("variation_name", ""),
                    "clinical_significance": germline.get("description", ""),
                    "conditions": conditions[:5],
                    "review_status": germline.get("review_status", ""),
                }
            )
        return {"source": "clinvar", "hits": len(variants), "data": variants, "error": None}
    except Exception as e:
        return _empty("clinvar", error=str(e))


async def fetch_pubmed(client: httpx.AsyncClient, query: str) -> dict[str, Any]:
    try:
        search_url = f"{EUTILS}/esearch.fcgi"
        search_resp = await _ncbi_get(
            client,
            search_url,
            _ncbi_params(
                db="pubmed",
                term=f"{query}[gene]",
                retmode="json",
                retmax=5,
            ),
        )
        search_resp.raise_for_status()
        ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return _empty("pubmed")

        fetch_url = f"{EUTILS}/efetch.fcgi"
        fetch_resp = await _ncbi_get(
            client,
            fetch_url,
            _ncbi_params(
                db="pubmed",
                id=",".join(ids),
                retmode="xml",
                rettype="abstract",
            ),
        )
        fetch_resp.raise_for_status()

        articles = _parse_pubmed_xml(fetch_resp.text)
        return {"source": "pubmed", "hits": len(articles), "data": articles, "error": None}
    except Exception as e:
        return _empty("pubmed", error=str(e))


def _parse_pubmed_xml(xml_text: str) -> list[dict[str, Any]]:
    articles: list[dict[str, Any]] = []
    try:
        xml_text = re.sub(r"<![^>]*>", "", xml_text)
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return articles

    for art in root.findall(".//PubmedArticle"):
        title_el = art.find(".//ArticleTitle")
        title = "".join(title_el.itertext()).strip() if title_el is not None else ""
        journal_el = art.find(".//Journal/Title")
        journal = journal_el.text.strip() if journal_el is not None and journal_el.text else ""
        year_el = art.find(".//PubDate/Year") or art.find(".//PubDate/MedlineDate")
        year = year_el.text.strip()[:4] if year_el is not None and year_el.text else ""

        authors: list[str] = []
        for au in art.findall(".//Author")[:3]:
            last = au.findtext("LastName") or ""
            initials = au.findtext("Initials") or ""
            name = f"{last} {initials}".strip()
            if name:
                authors.append(name)

        abstract_parts: list[str] = []
        for ab in art.findall(".//Abstract/AbstractText"):
            abstract_parts.append("".join(ab.itertext()))
        abstract = re.sub(r"\s+", " ", " ".join(abstract_parts)).strip()
        snippet = abstract[:300]

        pmid_el = art.find(".//PMID")
        pmid = pmid_el.text.strip() if pmid_el is not None and pmid_el.text else ""

        if title or abstract:
            articles.append(
                {
                    "pmid": pmid,
                    "title": title,
                    "authors": authors,
                    "journal": journal,
                    "year": year,
                    "abstract_snippet": snippet,
                }
            )
    return articles


async def fetch_uniprot(client: httpx.AsyncClient, query: str) -> dict[str, Any]:
    try:
        params = {
            "query": f"gene:{query} AND organism_id:9606",
            "format": "json",
            "size": 3,
        }
        resp = await client.get(UNIPROT, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        body = resp.json()
        results = body.get("results", []) or []

        proteins: list[dict[str, Any]] = []
        for entry in results:
            entry_type = entry.get("entryType", "")
            reviewed = "Reviewed" in entry_type or "Swiss-Prot" in entry_type
            if not reviewed:
                continue
            protein_desc = entry.get("proteinDescription", {}) or {}
            rec_name = protein_desc.get("recommendedName", {}) or {}
            protein_name = (rec_name.get("fullName", {}) or {}).get("value", "")

            gene_names: list[str] = []
            for g in entry.get("genes", []) or []:
                gname = (g.get("geneName", {}) or {}).get("value")
                if gname:
                    gene_names.append(gname)

            function_text = ""
            for c in entry.get("comments", []) or []:
                if c.get("commentType") == "FUNCTION":
                    texts = c.get("texts", []) or []
                    if texts:
                        function_text = texts[0].get("value", "")
                        break

            sequence_length = (entry.get("sequence", {}) or {}).get("length", 0)
            proteins.append(
                {
                    "accession": entry.get("primaryAccession", ""),
                    "protein_name": protein_name,
                    "gene_names": gene_names,
                    "function": function_text,
                    "sequence_length": sequence_length,
                    "reviewed": True,
                }
            )
        return {"source": "uniprot", "hits": len(proteins), "data": proteins, "error": None}
    except Exception as e:
        return _empty("uniprot", error=str(e))


async def fetch_all(query: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        clinvar = await fetch_clinvar(client, query)
        await asyncio.sleep(0.5)
        pubmed = await fetch_pubmed(client, query)
        uniprot = await fetch_uniprot(client, query)
    return [clinvar, pubmed, uniprot]
