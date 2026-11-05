"""Optional external research retrieval (arXiv public API, no key required).

Every returned record comes straight from the API response; nothing is invented.
"""
from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, List

_NS = {"a": "http://www.w3.org/2005/Atom"}


def fetch_arxiv(query_terms: List[str], max_results: int = 5, timeout: int = 15) -> List[Dict[str, str]]:
    terms = [t for t in query_terms if t][:6]
    if not terms:
        return []
    q = " OR ".join(f'all:"{t}"' if " " in t else f"all:{t}" for t in terms)
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": q, "start": 0, "max_results": max_results, "sortBy": "relevance"})
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "IdeaBridge/1.0"}),
                                timeout=timeout) as r:
        root = ET.fromstring(r.read())
    out = []
    for e in root.findall("a:entry", _NS):
        link = (e.findtext("a:id", default="", namespaces=_NS) or "").strip()
        title = " ".join((e.findtext("a:title", default="", namespaces=_NS) or "").split())
        summary = " ".join((e.findtext("a:summary", default="", namespaces=_NS) or "").split())
        if link and title:
            out.append({"id": link, "title": title, "summary": summary, "url": link})
    return out
