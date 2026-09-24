import re
import unicodedata
from difflib import SequenceMatcher

from procurement.models import WhitelistItem


class ProcurementKnowledgeRetriever:
    """Extension point for a future vector-backed policy/SOP retriever."""

    def retrieve(self, query, *, limit=3):
        return []


class ProcurementContextService:
    PROCUREMENT_HINTS = ("采购", "购买", "买", "白名单", "经费", "耗材", "药品")

    def __init__(self, *, knowledge_retriever=None):
        self.knowledge_retriever = knowledge_retriever or ProcurementKnowledgeRetriever()

    @staticmethod
    def normalize(value):
        value = unicodedata.normalize("NFKC", str(value or "")).lower()
        return re.sub(r"[^0-9a-z_\u4e00-\u9fff]", "", value)

    @classmethod
    def looks_like_procurement(cls, query):
        normalized = cls.normalize(query)
        return any(hint in normalized for hint in cls.PROCUREMENT_HINTS)

    @classmethod
    def _score(cls, query, row):
        normalized_query = cls.normalize(query)
        terms = [
            row.get("content"),
            row.get("manufacturer"),
            row.get("cas_number"),
            row.get("product_number"),
        ]
        scores = []
        for raw_term in terms:
            term = cls.normalize(raw_term)
            if not term:
                continue
            if term in normalized_query:
                scores.append(1.0 if raw_term == row.get("content") else 0.94)
                continue
            if len(term) < 2:
                continue
            match = SequenceMatcher(None, term, normalized_query).find_longest_match()
            coverage = match.size / len(term)
            overlap = len(set(term) & set(normalized_query)) / max(len(set(term)), 1)
            scores.append(coverage * 0.75 + overlap * 0.25)
        return max(scores, default=0.0)

    def search_candidates(self, query, *, limit=5):
        fields = (
            "id",
            "content",
            "main_category",
            "platform",
            "purchase_type",
            "manufacturer",
            "cas_number",
            "product_number",
            "parameters",
            "specifications",
        )
        rows = list(WhitelistItem.objects.values(*fields))
        ranked = []
        for row in rows:
            score = self._score(query, row)
            if score >= 0.55:
                ranked.append((score, row))
        ranked.sort(key=lambda item: (-item[0], len(item[1]["content"])))
        result = []
        for score, row in ranked[:limit]:
            compact = dict(row)
            compact["match_score"] = round(score, 3)
            result.append(compact)
        return result

    def prefetch(self, query):
        if not self.looks_like_procurement(query):
            return {}
        candidates = self.search_candidates(query)
        knowledge = self.knowledge_retriever.retrieve(query, limit=3)
        if not candidates and not knowledge:
            return {}
        return {
            "whitelist_candidates": candidates,
            "knowledge_chunks": knowledge,
            "notice": "候选项只用于辅助理解；最终平台和经费类型由后端规则再次校验。",
        }

