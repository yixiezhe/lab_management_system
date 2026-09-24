import re
import unicodedata
from difflib import SequenceMatcher

from equipment.services.query_service import EquipmentQueryService


class EquipmentContextService:
    EQUIPMENT_HINTS = (
        "仪器",
        "预约",
        "通道",
        "输力强",
        "电化学",
        "xrd",
        "球磨",
        "手套箱",
        "马弗炉",
        "管式炉",
        "封管机",
    )
    CHINESE_DIGITS = {
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
    }

    @staticmethod
    def normalize(value):
        value = unicodedata.normalize("NFKC", str(value or "")).lower()
        return re.sub(r"[^0-9a-z\u4e00-\u9fff]", "", value)

    @classmethod
    def looks_like_equipment(cls, query):
        normalized = cls.normalize(query)
        return any(hint in normalized for hint in cls.EQUIPMENT_HINTS)

    @classmethod
    def extract_position_no(cls, query):
        normalized = cls.normalize(query)
        if not any(alias in normalized for alias in ("输力强", "电化学")):
            return None
        patterns = (
            r"(?:通道|第)([一二三四五六七八1-8])号?",
            r"([一二三四五六七八1-8])号(?:输力强|电化学)",
            r"(?:输力强|电化学工作站|电化学)([一二三四五六七八1-8])号?",
        )
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                value = match.group(1)
                return cls.CHINESE_DIGITS.get(value, int(value) if value.isdigit() else None)
        return None

    @classmethod
    def _score(cls, query, row):
        normalized_query = cls.normalize(query)
        name = cls.normalize(row.get("name"))
        if name and name in normalized_query:
            return 1.0

        aliases = []
        mode = row.get("booking_mode")
        if mode == "electrochemical_workstation":
            aliases = ["输力强", "电化学", "电化学工作站"]
        elif mode == "xrd":
            aliases = ["xrd", "衍射"]
        for alias in aliases:
            if alias in normalized_query:
                return 0.98

        if not name:
            return 0.0
        match = SequenceMatcher(None, name, normalized_query).find_longest_match()
        coverage = match.size / len(name)
        return coverage if coverage >= 0.5 else 0.0

    def search_candidates(self, actor, query, *, limit=3):
        fields = (
            "id",
            "name",
            "booking_mode",
            "time_unit_minutes",
            "open_time_start",
            "open_time_end",
        )
        rows = list(EquipmentQueryService.visible_equipment(actor).values(*fields))
        ranked = [(self._score(query, row), row) for row in rows]
        ranked = [item for item in ranked if item[0] >= 0.5]
        ranked.sort(key=lambda item: (-item[0], len(item[1]["name"])))
        return [
            {**row, "match_score": round(score, 3)}
            for score, row in ranked[:limit]
        ]

    def prefetch(self, query, actor):
        if not getattr(actor, "is_authenticated", False):
            return {}
        if not self.looks_like_equipment(query):
            return {}
        candidates = self.search_candidates(actor, query)
        position_no = self.extract_position_no(query)
        if not candidates and position_no is None:
            return {}
        return {
            "equipment_candidates": candidates,
            "extracted_position_no": position_no,
            "notice": (
                "候选仪器与通道号由后端从当前可见仪器中解析；"
                "准备预约前仍须调用工具校验日期、时段和冲突。"
            ),
        }
