"""BM25 keyword search for tickets."""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from vtic.errors import TicketReadError
from vtic.models import SearchFilters, SearchResponse, SearchResult, Ticket
from vtic.storage import TicketStore


_TOKEN_SPLIT_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class _CorpusCacheEntry:
    ticket: Ticket
    mtime_ns: int
    signature: str
    tokenized_document: list[str]


class _BuiltinBM25:
    """Minimal BM25Okapi-compatible scorer for tokenized documents."""

    _K1 = 1.5
    _B = 0.75

    def __init__(self, corpus: list[list[str]]) -> None:
        self._corpus_size = len(corpus)
        self._doc_lengths = [len(document) for document in corpus]
        self._avgdl = (
            sum(self._doc_lengths) / self._corpus_size if self._corpus_size > 0 else 0.0
        )
        self._doc_term_freqs: list[dict[str, int]] = []
        self._idf: dict[str, float] = {}

        doc_freqs: dict[str, int] = {}
        for document in corpus:
            term_freqs: dict[str, int] = {}
            for term in document:
                term_freqs[term] = term_freqs.get(term, 0) + 1
            self._doc_term_freqs.append(term_freqs)

            for term in term_freqs:
                doc_freqs[term] = doc_freqs.get(term, 0) + 1

        for term, document_count in doc_freqs.items():
            self._idf[term] = math.log(
                (self._corpus_size - document_count + 0.5) / (document_count + 0.5) + 1
            )

    def get_scores(self, query: list[str]) -> list[float]:
        """Return BM25 scores for each indexed document."""

        if self._corpus_size == 0:
            return []

        scores: list[float] = []
        for term_freqs, doc_length in zip(self._doc_term_freqs, self._doc_lengths, strict=True):
            length_norm = 1 - self._B
            if self._avgdl > 0:
                length_norm += self._B * doc_length / self._avgdl

            score = 0.0
            for term in query:
                frequency = term_freqs.get(term, 0)
                if frequency <= 0:
                    continue
                idf = self._idf.get(term)
                if idf is None:
                    continue
                numerator = frequency * (self._K1 + 1)
                denominator = frequency + self._K1 * length_norm
                score += idf * (numerator / denominator)
            scores.append(score)

        return scores


class TicketSearch:
    """BM25-based keyword search over ticket text."""

    def __init__(self, store: TicketStore) -> None:
        self.store = store
        self._tickets: list[Ticket] = []
        self._tokenized_documents: list[list[str]] = []
        self._ticket_signatures: tuple[str, ...] = ()
        self._bm25: _BuiltinBM25 | None = None
        self._index_path = self.store.base_dir / ".vtic-search-index.json"
        self._corpus_cache: dict[Path, _CorpusCacheEntry] = {}

    def _tokenize(self, text: str) -> list[str]:
        """Split text on non-alphanumeric characters and drop short tokens."""

        if not text:
            return []
        return [token for token in _TOKEN_SPLIT_RE.split(text.lower()) if len(token) >= 2]

    def _get_document(self, ticket: Ticket) -> str:
        """Return the searchable document text for a ticket."""

        return ticket.search_text

    def _ticket_signature(self, ticket: Ticket) -> str:
        """Return a stable signature for cache invalidation."""

        payload = {
            "id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "fix": ticket.fix,
            "file": ticket.file,
            "tags": ticket.tags,
            "updated_at": ticket.updated_at.isoformat(),
            "version": ticket.version,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def _set_index_state(
        self,
        tickets: list[Ticket],
        tokenized_documents: list[list[str]],
    ) -> None:
        """Update the active in-memory index state."""

        self._tickets = list(tickets)
        self._tokenized_documents = [list(document) for document in tokenized_documents]
        self._ticket_signatures = tuple(
            self._ticket_signature(ticket) for ticket in self._tickets
        )
        self._bm25 = (
            _BuiltinBM25(self._tokenized_documents)
            if self._tokenized_documents
            else None
        )

    def _persist_index(self) -> None:
        """Persist the current index to disk for future processes."""

        if not self.store.base_dir.exists():
            return

        payload = {
            "version": 1,
            "ticket_signatures": list(self._ticket_signatures),
            "tokenized_documents": self._tokenized_documents,
        }
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8",
            dir=self._index_path.parent, delete=False,
        ) as tmp:
            tmp.write(json.dumps(payload))
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, self._index_path)

    def _load_persisted_index(self, tickets: list[Ticket]) -> bool:
        """Load a persisted index when it matches the current ticket corpus."""

        if not self._index_path.exists():
            return False

        try:
            payload = json.loads(self._index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False

        if payload.get("version") != 1:
            return False

        signatures = tuple(self._ticket_signature(ticket) for ticket in tickets)
        cached_signatures = tuple(payload.get("ticket_signatures", []))
        tokenized_documents = payload.get("tokenized_documents")
        if (
            signatures != cached_signatures
            or not isinstance(tokenized_documents, list)
            or len(tokenized_documents) != len(tickets)
        ):
            return False

        if any(not isinstance(document, list) for document in tokenized_documents):
            return False

        self._set_index_state(
            tickets,
            [
                [str(token) for token in document]
                for document in tokenized_documents
            ],
        )
        return True

    def build_index(
        self,
        tickets: list[Ticket] | None = None,
        *,
        persist: bool = False,
    ) -> None:
        """Build or rebuild the BM25 index for the provided ticket corpus."""

        corpus = list(tickets) if tickets is not None else self.store.list()
        tokenized_documents = [self._tokenize(self._get_document(ticket)) for ticket in corpus]
        self._set_index_state(corpus, tokenized_documents)
        if persist:
            self._persist_index()

    def _load_cached_tickets(self) -> list[Ticket]:
        """Load tickets, re-parsing only files whose mtimes changed."""

        tickets: list[Ticket] = []
        next_cache: dict[Path, _CorpusCacheEntry] = {}

        for path in self.store._iter_ticket_paths():
            try:
                mtime_ns = path.stat().st_mtime_ns
            except OSError:
                continue

            entry = self._corpus_cache.get(path)
            if entry is None or entry.mtime_ns != mtime_ns:
                try:
                    ticket = self.store._read_ticket(path)
                except TicketReadError:
                    continue
                entry = _CorpusCacheEntry(
                    ticket=ticket,
                    mtime_ns=mtime_ns,
                    signature=self._ticket_signature(ticket),
                    tokenized_document=self._tokenize(self._get_document(ticket)),
                )

            next_cache[path] = entry
            tickets.append(entry.ticket)

        self._corpus_cache = next_cache
        return sorted(tickets, key=self._ticket_sort_key)

    def _rebuild_index_from_cache(self, tickets: list[Ticket]) -> None:
        """Rebuild the BM25 state from cached metadata and tokenized content."""

        tokenized_documents = []
        for ticket in tickets:
            path = self.store.base_dir / ticket.filepath
            entry = self._corpus_cache.get(path)
            if entry is None:
                tokenized_documents.append(self._tokenize(self._get_document(ticket)))
                continue
            tokenized_documents.append(list(entry.tokenized_document))
        self._set_index_state(tickets, tokenized_documents)

    def _ensure_index(self, tickets: list[Ticket]) -> None:
        """Ensure the cached index matches the current ticket corpus."""

        signatures = tuple(self._ticket_signature(ticket) for ticket in tickets)
        if self._bm25 is not None and self._ticket_signatures == signatures:
            return
        if self._load_persisted_index(tickets):
            return
        if self._ticket_signatures != signatures or self._bm25 is None:
            self._rebuild_index_from_cache(tickets)

    def _build_result(
        self,
        ticket: Ticket,
        *,
        score: float,
        bm25_score: float | None,
        query_terms: list[str],
    ) -> SearchResult:
        """Convert a ticket and its scores into a SearchResult."""

        content_terms = set(self._tokenize(f"{ticket.title} {ticket.description or ''}"))
        highlights: list[str] = []
        for term in query_terms:
            if term in content_terms and term not in highlights:
                highlights.append(term)

        return SearchResult(
            id=ticket.id,
            title=ticket.title,
            repo=ticket.repo,
            category=ticket.category.value,
            severity=ticket.severity.value,
            status=ticket.status.value,
            description=ticket.description,
            slug=ticket.slug,
            score=score,
            bm25_score=bm25_score,
            semantic_score=None,
            highlights=highlights,
        )

    @staticmethod
    def _ticket_sort_key(ticket: Ticket) -> tuple[str, int]:
        """Sort tickets by stable ticket ID ordering."""

        return (ticket.id[0], int(ticket.id[1:]))

    def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        topk: int = 10,
        offset: int = 0,
    ) -> SearchResponse:
        """Search tickets using BM25 keyword ranking."""

        started_at = time.perf_counter()
        normalized_query = query.strip()
        tickets = self._load_cached_tickets()

        if not tickets:
            took_ms = math.ceil((time.perf_counter() - started_at) * 1000)
            return SearchResponse(
                results=[],
                total=0,
                query=normalized_query,
                semantic=False,
                limit=topk,
                offset=offset,
                has_more=False,
                took_ms=took_ms,
            )

        self._ensure_index(tickets)
        query_terms = self._tokenize(normalized_query)
        filtered_tickets = [
            ticket for ticket in tickets if self.store._matches_filters(ticket, filters)
        ]

        if not query_terms:
            sorted_tickets = sorted(filtered_tickets, key=self._ticket_sort_key)
            page = sorted_tickets[offset : offset + topk]
            results = [
                self._build_result(ticket, score=1.0, bm25_score=None, query_terms=[])
                for ticket in page
            ]
            took_ms = math.ceil((time.perf_counter() - started_at) * 1000)
            return SearchResponse(
                results=results,
                total=len(sorted_tickets),
                query=normalized_query,
                semantic=False,
                limit=topk,
                offset=offset,
                has_more=(offset + len(results)) < len(sorted_tickets),
                took_ms=took_ms,
            )

        if self._bm25 is None:
            took_ms = math.ceil((time.perf_counter() - started_at) * 1000)
            return SearchResponse(
                results=[],
                total=0,
                query=normalized_query,
                semantic=False,
                limit=topk,
                offset=offset,
                has_more=False,
                took_ms=took_ms,
            )

        raw_scores = self._bm25.get_scores(query_terms)
        if not raw_scores:
            took_ms = math.ceil((time.perf_counter() - started_at) * 1000)
            return SearchResponse(
                results=[],
                total=0,
                query=normalized_query,
                semantic=False,
                limit=topk,
                offset=offset,
                has_more=False,
                took_ms=took_ms,
            )

        max_score = max(raw_scores)
        ranked: list[tuple[Ticket, float, float]] = []

        if max_score > 0:
            # Normal BM25 ranking — exclude non-matching documents
            for ticket, raw_score in zip(self._tickets, raw_scores, strict=True):
                if not self.store._matches_filters(ticket, filters):
                    continue
                if raw_score <= 0:
                    continue
                normalized_score = raw_score / max_score
                ranked.append((ticket, normalized_score, float(raw_score)))
        else:
            # BM25 returns all non-positive scores with very small corpora
            # (IDF penalty outweighs TF boost). Fall back to term-frequency matching.
            query_terms_set = set(query_terms)
            for ticket in filtered_tickets:
                doc_terms = set(self._tokenize(ticket.search_text))
                overlap = len(query_terms_set & doc_terms)
                if overlap > 0:
                    ranked.append((ticket, overlap / len(query_terms_set), 0.0))

        ranked.sort(key=lambda item: (-item[1], self._ticket_sort_key(item[0])))

        page = ranked[offset : offset + topk]
        results = [
            self._build_result(
                ticket,
                score=normalized_score,
                bm25_score=raw_score,
                query_terms=query_terms,
            )
            for ticket, normalized_score, raw_score in page
        ]

        took_ms = math.ceil((time.perf_counter() - started_at) * 1000)
        # Note: total asymmetry between BM25 and fallback paths:
        # - Normal path: total = tickets with positive BM25 score > 0
        # - Fallback path: total = tickets with any query term overlap
        # Both are reasonable; API consumers should treat total as approximate.
        return SearchResponse(
            results=results,
            total=len(ranked),
            query=normalized_query,
            semantic=False,
            limit=topk,
            offset=offset,
            has_more=(offset + len(results)) < len(ranked),
            took_ms=took_ms,
        )
