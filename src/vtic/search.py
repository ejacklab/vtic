"""BM25 keyword search for tickets."""

from __future__ import annotations

import math
import re
import time

from vtic.models import SearchFilters, SearchResponse, SearchResult, Ticket
from vtic.storage import TicketStore


_TOKEN_SPLIT_RE = re.compile(r"[^a-z0-9]+")


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
        self._ticket_ids: tuple[str, ...] = ()
        self._bm25: _BuiltinBM25 | None = None

    def _tokenize(self, text: str) -> list[str]:
        """Split text on non-alphanumeric characters and drop short tokens."""

        if not text:
            return []
        return [token for token in _TOKEN_SPLIT_RE.split(text.lower()) if len(token) >= 2]

    def _get_document(self, ticket: Ticket) -> str:
        """Return the searchable document text for a ticket."""

        return ticket.search_text

    def build_index(self, tickets: list[Ticket] | None = None) -> None:
        """Build or rebuild the BM25 index for the provided ticket corpus."""

        corpus = list(tickets) if tickets is not None else self.store.list()
        self._tickets = corpus
        self._ticket_ids = tuple(ticket.id for ticket in corpus)
        self._tokenized_documents = [self._tokenize(self._get_document(ticket)) for ticket in corpus]

        if not self._tokenized_documents:
            self._bm25 = None
            return

        self._bm25 = _BuiltinBM25(self._tokenized_documents)

    def _ensure_index(self, tickets: list[Ticket]) -> None:
        """Ensure the cached index matches the current ticket corpus."""

        ticket_ids = tuple(ticket.id for ticket in tickets)
        if self._bm25 is None or self._ticket_ids != ticket_ids:
            self.build_index(tickets)

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
        tickets = self.store.list(filters)

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

        if not query_terms:
            sorted_tickets = sorted(tickets, key=self._ticket_sort_key)
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
            for ticket, raw_score in zip(tickets, raw_scores, strict=True):
                if raw_score <= 0:
                    continue
                normalized_score = raw_score / max_score
                ranked.append((ticket, normalized_score, float(raw_score)))
        else:
            # BM25 returns all non-positive scores with very small corpora
            # (IDF penalty outweighs TF boost). Fall back to term-frequency matching.
            query_terms_set = set(query_terms)
            for ticket in tickets:
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
