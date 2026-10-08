"""Optional, bounded metadata enrichment for selected public AI news URLs.

Reads only a page's public HTML metadata (description / og:description). Does
not scrape paywalled article bodies, copy copyrighted articles, bypass robots,
or treat publisher assertions as independently verified facts.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

TRUSTED_HOSTS = (
    "techcrunch.com", "theverge.com", "technologyreview.com",
    "research.google", "research.google.com", "arxiv.org",
    "huggingface.co",
)
LIMIT_BYTES = 260_000

def trusted(url):
    try:
        p = urlsplit(url)
        host = (p.hostname or "").lower()
        return (p.scheme == "https" and not p.username and not p.password and
                any(host == allowed or host.endswith("." + allowed) for allowed in TRUSTED_HOSTS))
    except ValueError:
        return False

class RestrictRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not trusted(newurl):
            raise ValueError("Redirect to non-allowlisted domain rejected")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.descriptions = []
        self.in_head = False
    def handle_starttag(self, tag, attrs):
        if tag == "head":
            self.in_head=True
        if tag != "meta" or not self.in_head:
            return
        props = dict((k.lower(), v or "") for k, v in attrs)
        attr = (props.get("property") or props.get("name") or "").lower()
        if attr in {"og:description", "description", "twitter:description"}:
            value = props.get("content", "")
            if value:self.descriptions.append(unescape(value).strip())
    def handle_endtag(self, tag):
        if tag == "head":self.in_head=False

def suitable(description, story):
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", description or "")).strip()
    if not 85 <= len(text) <= 900:return ""
    if re.search(r"(?i)subscribe now|sign up for|read more|cookie policy|register now|tickets|promotion",text):
        return ""
    if len(text.split()) < 15:return ""
    title_tokens={w for w in re.findall(r"[a-z]{4,}",story.get("title","").lower()) if w not in {"with","from","that","this","what","about","news","latest","into","over"}}
    description_tokens=set(re.findall(r"[a-z]{4,}",text.lower()))
    if title_tokens and not (title_tokens & description_tokens):
        return ""
    if re.search(r"(?i)(ignore previous instructions|system prompt|<script|you are now)",text):
        return ""
    return text[:520]

def describe(story, retrieve=None):
    """Safely extend RSS metadata, never silently change news source attribution."""
    url=story.get("url","")
    if not trusted(url):
        return None
    try:
        if retrieve:
            content=retrieve(url)
        else:
            opener=build_opener(RestrictRedirect())
            req=Request(url,headers={"User-Agent":"AIDailyIntelligence/7.0 educational metadata reader","Accept":"text/html"})
            with opener.open(req,timeout=7) as response:
                if "html" not in response.headers.get("Content-Type","").lower():
                    return None
                content=response.read(LIMIT_BYTES+1)
        if len(content)>LIMIT_BYTES:return None
        parser=MetaParser()
        parser.feed(content.decode("utf-8","replace"))
        original=story.get("excerpt","")
        candidates=[suitable(d,story) for d in parser.descriptions]
        candidates=[c for c in candidates if len(c)>=max(100,len(original)+35)]
        return max(candidates,key=len) if candidates else None
    except (OSError,ValueError,UnicodeError,RuntimeError):
        return None

def enrich(stories, retrieve=None):
    if not stories:
        return {"metadata_checked":0,"metadata_enriched":0}
    with ThreadPoolExecutor(max_workers=min(4,len(stories))) as pool:
        matches=list(pool.map(lambda row:describe(row,retrieve=retrieve),stories))
    count=0
    for story,metadata in zip(stories,matches):
        if metadata:
            story["excerpt"]=metadata
            story["excerpt_origin"]="publisher_public_metadata"
            count+=1
    return {"metadata_checked":len(stories),"metadata_enriched":count}
