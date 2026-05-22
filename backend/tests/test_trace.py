import os
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
import respx
from httpx import ASGITransport, AsyncClient, Response

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.agents import fetcher
from app.agents.synthesizer import compute_eval_score, has_all_sections, synthesize
from app.database import Base, engine
from app.main import app


CLINVAR_SEARCH_JSON = {"esearchresult": {"idlist": ["12345", "67890"]}}
CLINVAR_SUMMARY_JSON = {
    "result": {
        "12345": {
            "title": "NM_000059.4(BRCA2):c.5946delT",
            "germline_classification": {
                "description": "Pathogenic",
                "review_status": "criteria provided, multiple submitters",
                "trait_set": [{"trait_name": "Hereditary breast and ovarian cancer syndrome"}],
            },
        },
        "67890": {
            "title": "NM_000059.4(BRCA2):c.6275_6276delTT",
            "germline_classification": {
                "description": "Pathogenic",
                "review_status": "reviewed by expert panel",
                "trait_set": [{"trait_name": "Familial cancer of breast"}],
            },
        },
    }
}

PUBMED_SEARCH_JSON = {"esearchresult": {"idlist": ["999"]}}
PUBMED_FETCH_XML = """<?xml version="1.0" ?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>999</PMID>
      <Article>
        <Journal><Title>Nature Genetics</Title></Journal>
        <ArticleTitle>BRCA2 functional reversion in metastatic cancer</ArticleTitle>
        <Abstract><AbstractText>This is a sample abstract describing BRCA2 reversion mutations and PARP inhibitor resistance.</AbstractText></Abstract>
        <AuthorList>
          <Author><LastName>Smith</LastName><Initials>J</Initials></Author>
          <Author><LastName>Doe</LastName><Initials>A</Initials></Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
    <PubmedData><History><PubMedPubDate><Year>2024</Year></PubMedPubDate></History></PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""

UNIPROT_JSON = {
    "results": [
        {
            "entryType": "UniProtKB reviewed (Swiss-Prot)",
            "primaryAccession": "P51587",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Breast cancer type 2 susceptibility protein"}}
            },
            "genes": [{"geneName": {"value": "BRCA2"}}],
            "comments": [
                {
                    "commentType": "FUNCTION",
                    "texts": [{"value": "Involved in double-strand break repair via homologous recombination."}],
                }
            ],
            "sequence": {"length": 3418},
        }
    ]
}


@pytest_asyncio.fixture(autouse=True)
async def _prepare_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@respx.mock
@pytest.mark.asyncio
async def test_fetch_all_returns_data_for_brca2():
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").mock(
        side_effect=[
            Response(200, json=CLINVAR_SEARCH_JSON),
            Response(200, json=PUBMED_SEARCH_JSON),
        ]
    )
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi").mock(
        return_value=Response(200, json=CLINVAR_SUMMARY_JSON)
    )
    respx.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi").mock(
        return_value=Response(200, text=PUBMED_FETCH_XML)
    )
    respx.get("https://rest.uniprot.org/uniprotkb/search").mock(
        return_value=Response(200, json=UNIPROT_JSON)
    )

    results = await fetcher.fetch_all("BRCA2")
    by_src = {r["source"]: r for r in results}

    assert by_src["clinvar"]["hits"] == 2
    assert by_src["pubmed"]["hits"] == 1
    assert by_src["uniprot"]["hits"] == 1
    assert by_src["clinvar"]["data"][0]["clinical_significance"] == "Pathogenic"
    assert "BRCA2" in by_src["pubmed"]["data"][0]["title"]
    assert by_src["uniprot"]["data"][0]["reviewed"] is True


@pytest.mark.asyncio
async def test_synthesizer_returns_all_five_sections():
    sources = [
        {"source": "clinvar", "hits": 1, "data": [{"variant_name": "v1", "clinical_significance": "Pathogenic", "conditions": ["X"]}], "error": None},
        {"source": "pubmed", "hits": 1, "data": [{"title": "t", "journal": "J", "year": "2024", "authors": [], "abstract_snippet": ""}], "error": None},
        {"source": "uniprot", "hits": 1, "data": [{"protein_name": "P", "function": "f", "sequence_length": 100, "reviewed": True, "accession": "P1"}], "error": None},
    ]
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
        os.environ.pop("OPENAI_API_KEY", None)
        brief = await synthesize("BRCA2", sources)
    assert has_all_sections(brief)


@pytest.mark.asyncio
async def test_eval_score_bounded_0_to_100():
    # Maxed: 3+ ClinVar, 3+ PubMed, 1+ UniProt, 250+ word brief → exactly 100.0
    sources_full = [
        {"source": "clinvar", "hits": 3, "data": [], "error": None},
        {"source": "pubmed", "hits": 5, "data": [], "error": None},
        {"source": "uniprot", "hits": 1, "data": [{"reviewed": True}], "error": None},
    ]
    brief = " ".join(["word"] * 300)
    score = compute_eval_score(brief, sources_full)
    assert 0 <= score <= 100
    assert score == 100.0

    # Proportional: 2/3 of ClinVar weight + 0 elsewhere → 20.0
    partial = [
        {"source": "clinvar", "hits": 2, "data": [], "error": None},
        {"source": "pubmed", "hits": 0, "data": [], "error": None},
        {"source": "uniprot", "hits": 0, "data": [], "error": None},
    ]
    assert compute_eval_score("", partial) == 20.0

    empty = [
        {"source": "clinvar", "hits": 0, "data": [], "error": None},
        {"source": "pubmed", "hits": 0, "data": [], "error": None},
        {"source": "uniprot", "hits": 0, "data": [], "error": None},
    ]
    assert compute_eval_score("short", empty) == 0.0


@pytest.mark.asyncio
async def test_post_trace_valid_query_returns_200():
    async def _stub_fetch_all(query: str):
        return [
            {"source": "clinvar", "hits": 1, "data": [{"variant_name": "v", "clinical_significance": "Pathogenic", "conditions": ["X"]}], "error": None},
            {"source": "pubmed", "hits": 1, "data": [{"title": "t", "journal": "J", "year": "2024", "authors": [], "abstract_snippet": ""}], "error": None},
            {"source": "uniprot", "hits": 1, "data": [{"protein_name": "P", "function": "f", "sequence_length": 100, "reviewed": True, "accession": "P1"}], "error": None},
        ]

    async def _stub_synth(query, sources):
        return (
            "GENE OVERVIEW:\nx.\nASSOCIATED CONDITIONS:\nx.\nPROTEIN FUNCTION:\nx.\n"
            "RECENT RESEARCH HIGHLIGHTS:\nx.\nCLINICAL SIGNIFICANCE SUMMARY:\nx."
        )

    with patch("app.routers.trace.fetch_all", new=AsyncMock(side_effect=_stub_fetch_all)), \
         patch("app.routers.trace.synthesize", new=AsyncMock(side_effect=_stub_synth)):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/trace", json={"query": "BRCA2"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "BRCA2"
    assert "brief" in body
    assert "eval_score" in body
    assert len(body["sources"]) == 3


@pytest.mark.asyncio
async def test_post_trace_empty_query_returns_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/trace", json={"query": ""})
    assert resp.status_code == 422
