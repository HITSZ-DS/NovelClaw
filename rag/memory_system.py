"""
Memory management system for dynamic, weighted memory retrieval.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import math
import os
import re
import shutil

from rag.vector_store import VectorStore
from rag.document_processor import DocumentProcessor
from config import Config


class MemorySystem:
    """Dynamic memory system with weighted storage, retrieval, and integration."""

    MEMORY_BUCKETS = (
        "texts",
        "outlines",
        "characters",
        "world_settings",
        "plot_points",
        "fact_cards",
    )

    BUCKET_TO_TYPE = {
        "texts": "generated_text",
        "outlines": "outline",
        "characters": "character",
        "world_settings": "world_setting",
        "plot_points": "plot_point",
        "fact_cards": "fact_card",
    }

    TYPE_BASE_WEIGHTS = {
        "outline": 0.88,
        "character": 0.82,
        "world_setting": 0.80,
        "plot_point": 0.76,
        "fact_card": 0.78,
        "generated_text": 0.58,
    }

    OUTLINE_KIND_BONUS = {
        "global_outline": 0.12,
        "rolling_summary": 0.11,
        "chapter_summary": 0.07,
        "chapter_plan": 0.05,
    }

    TEXT_SOURCE_BONUS = {
        "chapter_final": 0.10,
        "chapter_draft": 0.04,
        "unfixed_segment": 0.03,
    }

    FACT_CARD_TYPE_BONUS = {
        "chapter_facts": 0.08,
        "timeline": 0.10,
        "foreshadowing": 0.08,
        "relationship": 0.06,
    }

    PLOT_POSITION_BONUS = {
        "opening": 0.05,
        "climax": 0.08,
        "ending": 0.06,
        "unknown": 0.0,
    }

    PRIORITY_BONUS = {
        "low": -0.05,
        "normal": 0.0,
        "medium": 0.0,
        "high": 0.08,
        "critical": 0.14,
    }

    MEMORY_TYPE_ALIASES = {
        "text": "generated_text",
        "generated_text": "generated_text",
        "outline": "outline",
        "character": "character",
        "world_setting": "world_setting",
        "plot_point": "plot_point",
        "fact_card": "fact_card",
    }

    NEED_KEYWORDS = {
        "character": [
            "人物", "角色", "主角", "配角", "关系", "动机", "心理", "性格", "身份",
            "character", "characters", "relationship", "motivation", "identity", "personality",
        ],
        "world": [
            "世界观", "设定", "规则", "地点", "组织", "学院", "力量", "能力", "阵营", "背景",
            "world", "setting", "rule", "rules", "location", "organization", "power", "background",
        ],
        "summary": [
            "承接", "衔接", "继续", "上一章", "前文", "摘要", "总结", "回顾",
            "continue", "continuity", "previous chapter", "summary", "recap",
        ],
        "plot": [
            "情节", "剧情", "推进", "冲突", "转折", "事件", "目标", "线索", "行动",
            "plot", "progress", "conflict", "turning point", "event", "goal", "clue", "action",
        ],
        "fact": [
            "事实", "约束", "必须", "不能", "时间线", "伏笔", "证据", "细节", "条件",
            "fact", "constraint", "must", "cannot", "timeline", "foreshadowing", "evidence", "detail",
        ],
    }

    def __init__(self, config: Config):
        self.config = config

        self.memory_store = VectorStore(
            config,
            collection_name="memory_collection",
            db_path=getattr(config, "memory_vector_db_path", None) or config.vector_db_path,
        )
        self.document_processor = DocumentProcessor(config)

        self.memory_index_path = os.path.join(
            getattr(config, "memory_vector_db_path", config.vector_db_path),
            "memory_index.json",
        )

        legacy_index_path = os.path.join(config.vector_db_path, "memory_index.json")
        if not os.path.exists(self.memory_index_path) and os.path.exists(legacy_index_path):
            try:
                os.makedirs(os.path.dirname(self.memory_index_path), exist_ok=True)
                shutil.copy2(legacy_index_path, self.memory_index_path)
            except Exception:
                pass

        self.memory_index = self._load_memory_index()
        self._normalize_memory_index()
        self._rebuild_entry_lookup()
        self._refresh_all_memory_weights()
        self._save_memory_index()

        if os.getenv("MIGRATE_LEGACY_MEMORY", "0") in {"1", "true", "True", "YES", "yes", "y"}:
            self._maybe_migrate_legacy_memory_collection()

    def _maybe_migrate_legacy_memory_collection(self):
        """
        Migrate legacy memory_collection from vector_db_path into memory_vector_db_path.
        """
        new_path = getattr(self.config, "memory_vector_db_path", None)
        if not new_path:
            return

        try:
            new_count = self.memory_store.get_collection_size()
        except Exception:
            new_count = 0
        if new_count and new_count > 0:
            return

        legacy_path = self.config.vector_db_path
        try:
            if os.path.abspath(legacy_path) == os.path.abspath(new_path):
                return
        except Exception:
            return

        try:
            import chromadb
            from chromadb.config import Settings

            legacy_client = chromadb.PersistentClient(
                path=legacy_path,
                settings=Settings(anonymized_telemetry=False),
            )
            legacy_col = legacy_client.get_collection("memory_collection")

            try:
                total = legacy_col.count()
            except Exception:
                total = 0

            if total <= 0:
                return

            batch_size = 200
            offset = 0
            while offset < total:
                res = legacy_col.get(
                    limit=batch_size,
                    offset=offset,
                    include=["documents", "metadatas", "embeddings"],
                )
                ids = res.get("ids") or []
                if not ids:
                    break

                self.memory_store.collection.add(
                    ids=ids,
                    documents=res.get("documents"),
                    metadatas=res.get("metadatas"),
                    embeddings=res.get("embeddings"),
                )
                offset += len(ids)

            print(f"[MemorySystem] 已从旧库迁移 memory_collection: {offset} 条 -> {new_path}")
        except Exception:
            return

    def _empty_memory_index(self) -> Dict:
        return {bucket: [] for bucket in self.MEMORY_BUCKETS}

    def _load_memory_index(self) -> Dict:
        """Load the structured memory index."""
        if os.path.exists(self.memory_index_path):
            try:
                with open(self.memory_index_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return self._empty_memory_index()
        return self._empty_memory_index()

    def _save_memory_index(self):
        """Persist the structured memory index."""
        os.makedirs(os.path.dirname(self.memory_index_path), exist_ok=True)
        with open(self.memory_index_path, "w", encoding="utf-8") as f:
            json.dump(self.memory_index, f, ensure_ascii=False, indent=2)

    def _normalize_memory_index(self):
        for bucket in self.MEMORY_BUCKETS:
            bucket_entries = self.memory_index.get(bucket)
            if not isinstance(bucket_entries, list):
                self.memory_index[bucket] = []
            else:
                self.memory_index[bucket] = bucket_entries

        now_iso = datetime.now().isoformat()
        for bucket in self.MEMORY_BUCKETS:
            for entry in self.memory_index.get(bucket, []):
                self._ensure_entry_defaults(entry, bucket, now_iso)

    def _ensure_entry_defaults(self, entry: Dict, bucket: str, now_iso: Optional[str] = None):
        now_iso = now_iso or datetime.now().isoformat()
        entry.setdefault("topic", "")
        entry.setdefault("timestamp", now_iso)
        entry.setdefault("content", "")
        if not isinstance(entry.get("metadata"), dict):
            entry["metadata"] = {}

        if bucket == "outlines" and not isinstance(entry.get("structure"), dict):
            entry["structure"] = {}
        if bucket == "characters" and not isinstance(entry.get("attributes"), dict):
            entry["attributes"] = {}
        if bucket == "plot_points":
            entry.setdefault("position", "unknown")
        if bucket == "fact_cards":
            entry.setdefault("card_type", entry.get("metadata", {}).get("card_type", "general"))

        access_stats = entry.get("access_stats")
        if not isinstance(access_stats, dict):
            access_stats = {}
            entry["access_stats"] = access_stats
        access_stats.setdefault("retrieval_count", 0)
        access_stats.setdefault("integration_count", 0)
        access_stats.setdefault("last_retrieved_at", None)
        access_stats.setdefault("last_integrated_at", None)

        weight_profile = entry.get("weight_profile")
        if not isinstance(weight_profile, dict):
            weight_profile = {}
            entry["weight_profile"] = weight_profile
        weight_profile.setdefault("base_importance", 0.0)
        weight_profile.setdefault("recency_score", 0.0)
        weight_profile.setdefault("reinforcement_score", 0.0)
        weight_profile.setdefault("dynamic_importance", 0.0)
        weight_profile.setdefault("last_score", 0.0)

    def _rebuild_entry_lookup(self):
        self._entry_by_id: Dict[str, Dict] = {}
        for bucket in self.MEMORY_BUCKETS:
            for entry in self.memory_index.get(bucket, []):
                memory_id = entry.get("id")
                if memory_id:
                    self._entry_by_id[memory_id] = entry

    def _register_entry(self, entry: Dict):
        memory_id = entry.get("id")
        if memory_id:
            self._entry_by_id[memory_id] = entry

    def _iter_entries(self):
        for bucket in self.MEMORY_BUCKETS:
            for entry in self.memory_index.get(bucket, []):
                yield bucket, entry

    def _normalize_memory_types(self, memory_types: Optional[List[str]]) -> Optional[List[str]]:
        if not memory_types:
            return None
        normalized = []
        for memory_type in memory_types:
            mapped = self.MEMORY_TYPE_ALIASES.get(memory_type, memory_type)
            if mapped not in normalized:
                normalized.append(mapped)
        return normalized

    def _infer_memory_type(
        self,
        bucket: Optional[str],
        entry: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        if metadata and metadata.get("type"):
            return metadata["type"]
        if entry:
            meta_type = entry.get("metadata", {}).get("type")
            if meta_type:
                return meta_type
        if bucket:
            return self.BUCKET_TO_TYPE.get(bucket, "generated_text")
        return "generated_text"

    def _parse_timestamp(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None

    def _days_since(self, value: Optional[str]) -> Optional[float]:
        parsed = self._parse_timestamp(value)
        if parsed is None:
            return None
        try:
            delta = datetime.now(parsed.tzinfo) - parsed if parsed.tzinfo else datetime.now() - parsed
            return max(0.0, delta.total_seconds() / 86400.0)
        except Exception:
            return None

    def _clamp(self, value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))

    def _to_float(self, value) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _extract_priority_bonus(self, entry: Dict) -> float:
        metadata = entry.get("metadata", {})
        priority = str(metadata.get("priority", metadata.get("importance_level", "normal"))).strip().lower()
        bonus = self.PRIORITY_BONUS.get(priority, 0.0)

        numeric_hint = None
        for key in ("importance", "weight", "priority_score"):
            numeric_hint = self._to_float(metadata.get(key))
            if numeric_hint is not None:
                break
        if numeric_hint is not None:
            bonus += (self._clamp(numeric_hint) - 0.5) * 0.35

        if metadata.get("pinned") or metadata.get("must_keep"):
            bonus += 0.12
        return bonus

    def _compute_base_importance(self, memory_type: str, entry: Dict) -> float:
        base = self.TYPE_BASE_WEIGHTS.get(memory_type, 0.58)

        if memory_type == "outline":
            kind = entry.get("structure", {}).get("kind")
            base += self.OUTLINE_KIND_BONUS.get(kind, 0.0)
        elif memory_type == "generated_text":
            source = entry.get("metadata", {}).get("source")
            base += self.TEXT_SOURCE_BONUS.get(source, 0.0)
        elif memory_type == "fact_card":
            card_type = entry.get("card_type") or entry.get("metadata", {}).get("card_type")
            base += self.FACT_CARD_TYPE_BONUS.get(card_type, 0.0)
        elif memory_type == "plot_point":
            base += self.PLOT_POSITION_BONUS.get(entry.get("position", "unknown"), 0.0)

        base += self._extract_priority_bonus(entry)
        return self._clamp(base, 0.05, 1.0)

    def _extract_current_chapter(self, query: str) -> Optional[int]:
        if not query:
            return None
        patterns = [
            r"\u7b2c\s*(\d+)\s*\u7ae0",
            r"chapter\s*(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, query, flags=re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except Exception:
                    return None
        return None

    def _count_keyword_hits(self, query: str, keywords: List[str]) -> int:
        if not query:
            return 0
        query_lower = query.lower()
        return sum(1 for keyword in keywords if keyword.lower() in query_lower)

    def _analyze_context_needs(self, query: str, current_chapter: Optional[int]) -> Dict[str, float]:
        needs = {
            "character": 1.0,
            "world": 0.95,
            "summary": 1.0,
            "plot": 1.0,
            "fact": 1.0,
        }
        if current_chapter is not None:
            needs["summary"] += 0.15
            needs["fact"] += 0.1
            needs["plot"] += 0.05

        for key, keywords in self.NEED_KEYWORDS.items():
            hits = self._count_keyword_hits(query, keywords)
            if hits > 0:
                needs[key] += min(0.9, hits * 0.22)

        return needs

    def _memory_need_boost(self, bucket: str, entry: Dict, needs: Dict[str, float]) -> float:
        memory_type = self._infer_memory_type(bucket, entry=entry)
        boost = 1.0
        if memory_type == "character":
            boost *= needs.get("character", 1.0)
        elif memory_type == "world_setting":
            boost *= needs.get("world", 1.0)
        elif memory_type == "plot_point":
            boost *= needs.get("plot", 1.0)
        elif memory_type == "fact_card":
            boost *= needs.get("fact", 1.0)
            if (entry.get("card_type") or entry.get("metadata", {}).get("card_type")) in {"timeline", "relationship"}:
                boost *= max(needs.get("summary", 1.0), needs.get("fact", 1.0))
        elif memory_type == "outline":
            kind = entry.get("structure", {}).get("kind")
            if kind in {"global_outline", "rolling_summary"}:
                boost *= max(needs.get("summary", 1.0), needs.get("plot", 1.0))
            elif kind in {"chapter_outline", "chapter_plan"}:
                boost *= max(needs.get("plot", 1.0), needs.get("summary", 1.0))
            elif kind == "chapter_summary":
                boost *= needs.get("summary", 1.0)
        return self._clamp(boost, 0.8, 2.2)

    def _entry_chapter(self, bucket: str, entry: Dict) -> Optional[int]:
        if bucket == "outlines":
            chapter = entry.get("structure", {}).get("chapter")
            if chapter is not None:
                try:
                    return int(chapter)
                except Exception:
                    return None
        metadata = entry.get("metadata", {}) or {}
        chapter = metadata.get("chapter")
        if chapter is not None:
            try:
                return int(chapter)
            except Exception:
                return None
        return None

    def _memory_horizon(self, bucket: str, entry: Dict) -> str:
        memory_type = self._infer_memory_type(bucket, entry=entry)
        if memory_type in {"character", "world_setting"}:
            return "anchor"
        if memory_type == "outline":
            kind = entry.get("structure", {}).get("kind")
            if kind in {"global_outline", "rolling_summary"}:
                return "anchor"
            if kind in {"chapter_outline", "chapter_plan", "chapter_summary", "consistency_issue"}:
                return "recent"
        if memory_type == "fact_card":
            card_type = entry.get("card_type") or entry.get("metadata", {}).get("card_type")
            if card_type in {"timeline", "relationship"}:
                return "anchor"
            return "recent"
        if memory_type == "plot_point":
            return "recent"
        return "detail"

    def _chapter_distance_weight(self, bucket: str, entry: Dict, current_chapter: Optional[int]) -> float:
        if current_chapter is None:
            return 1.0

        memory_type = self._infer_memory_type(bucket, entry=entry)
        horizon = self._memory_horizon(bucket, entry)
        chapter = self._entry_chapter(bucket, entry)
        if chapter is None:
            return max(0.85, 1.0 - float(getattr(self.config, "memory_anchor_decay_factor", 0.35))) if horizon == "anchor" else 1.0

        if chapter > current_chapter:
            return 0.0

        distance = current_chapter - chapter
        if horizon == "anchor":
            decay = float(getattr(self.config, "memory_anchor_decay_factor", 0.35))
            return self._clamp(1.0 - min(0.3, distance * 0.02) * decay, 0.85, 1.0)

        if memory_type == "generated_text":
            return 1.0 if distance == 0 else 0.0

        if memory_type == "outline":
            kind = entry.get("structure", {}).get("kind")
            if kind == "chapter_summary":
                window = max(1, int(getattr(self.config, "memory_recent_chapter_window", 1)))
                return 1.0 if distance <= window else 0.0
            if kind in {"chapter_outline", "chapter_plan", "consistency_issue"}:
                return 1.0 if distance <= 1 else 0.0

        if memory_type == "fact_card":
            window = max(1, int(getattr(self.config, "memory_fact_chapter_window", 2)))
            if distance <= window:
                return self._clamp(1.0 - distance * 0.18, 0.4, 1.0)
            return 0.0

        if memory_type == "plot_point":
            return self._clamp(1.0 - distance * 0.25, 0.0, 1.0)

        return 1.0

    def _coerce_text(self, value) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, dict):
            preferred_parts: List[str] = []
            for key in ("content", "text", "summary", "description", "title", "name"):
                part = value.get(key)
                if part is None:
                    continue
                rendered = self._coerce_text(part)
                if rendered:
                    preferred_parts.append(rendered)
            if preferred_parts:
                return "\n".join(preferred_parts)
            try:
                return json.dumps(value, ensure_ascii=False, sort_keys=True)
            except Exception:
                return str(value)
        if isinstance(value, (list, tuple, set)):
            parts = [self._coerce_text(item) for item in value]
            return "\n".join(part for part in parts if part)
        return str(value)

    def _keyword_score(self, query: str, text: str) -> float:
        query_text = self._coerce_text(query)
        text_value = self._coerce_text(text)
        if not query_text or not text_value:
            return 0.0
        query_tokens = {tok.lower() for tok in re.findall(r"[A-Za-z0-9\u4e00-\u9fff]{2,}", query_text)}
        if not query_tokens:
            return 0.0
        text_lower = text_value.lower()
        hits = sum(1 for token in query_tokens if token in text_lower)
        return self._clamp(hits / max(len(query_tokens), 1))

    def _iter_candidate_entries(
        self,
        topic: Optional[str],
        normalized_types: Optional[List[str]],
        current_chapter: Optional[int],
    ) -> List[Tuple[str, Dict]]:
        candidates: List[Tuple[str, Dict]] = []
        for bucket, entry in self._iter_entries():
            if topic and entry.get("topic") != topic:
                continue
            memory_type = self._infer_memory_type(bucket, entry=entry)
            if normalized_types and memory_type not in normalized_types:
                continue
            if self._chapter_distance_weight(bucket, entry, current_chapter) <= 0:
                continue
            candidates.append((bucket, entry))
        return candidates

    def _build_focus_corpus(self, topic: str, current_chapter: Optional[int], query: str) -> str:
        parts = [query or ""]
        if current_chapter is not None:
            for outline in self.memory_index.get("outlines", []):
                if outline.get("topic") != topic:
                    continue
                structure = outline.get("structure", {}) or {}
                kind = structure.get("kind")
                chapter = structure.get("chapter")
                if kind in {"chapter_outline", "chapter_plan"} and chapter == current_chapter:
                    parts.append(outline.get("content", ""))
                elif kind == "chapter_summary" and chapter in {current_chapter, current_chapter - 1}:
                    parts.append(outline.get("content", ""))
            for card in self.memory_index.get("fact_cards", []):
                if card.get("topic") != topic:
                    continue
                chapter = (card.get("metadata", {}) or {}).get("chapter")
                try:
                    chapter = int(chapter) if chapter is not None else None
                except Exception:
                    chapter = None
                if chapter is not None and current_chapter - 1 <= chapter <= current_chapter:
                    parts.append(card.get("content", ""))
        return "\n".join(p for p in parts if p)

    def _entity_focus_score(self, name: str, focus_corpus: str) -> float:
        if not name or not focus_corpus:
            return 0.0
        hits = len(re.findall(re.escape(name), focus_corpus, flags=re.IGNORECASE))
        if hits <= 0:
            return 0.0
        return self._clamp(0.45 + 0.2 * min(hits, 4), 0.0, 1.0)

    def _score_weights(self, include_semantic: bool = True) -> Dict[str, float]:
        weights = {
            "semantic": max(0.0, float(getattr(self.config, "memory_score_semantic_weight", 0.5))),
            "importance": max(0.0, float(getattr(self.config, "memory_score_importance_weight", 0.25))),
            "recency": max(0.0, float(getattr(self.config, "memory_score_recency_weight", 0.15))),
            "reinforcement": max(
                0.0, float(getattr(self.config, "memory_score_reinforcement_weight", 0.1))
            ),
        }
        if not include_semantic:
            weights.pop("semantic", None)
        total = sum(weights.values())
        if total <= 0:
            equal = 1.0 / max(len(weights), 1)
            return {key: equal for key in weights}
        return {key: value / total for key, value in weights.items()}

    def _compute_recency_score(self, entry: Dict) -> float:
        age_days = self._days_since(entry.get("timestamp"))
        if age_days is None:
            return 0.5
        half_life = max(0.1, float(getattr(self.config, "memory_recency_half_life_days", 14)))
        return self._clamp(math.pow(0.5, age_days / half_life))

    def _compute_reinforcement_score(self, entry: Dict) -> float:
        access_stats = entry.get("access_stats", {})
        retrieval_count = max(0, int(access_stats.get("retrieval_count", 0) or 0))
        integration_count = max(0, int(access_stats.get("integration_count", 0) or 0))
        cap = max(1.0, float(getattr(self.config, "memory_reinforcement_cap", 12)))

        raw = integration_count * 1.5 + retrieval_count * 0.5
        score = min(1.0, raw / cap)

        latest_touch = access_stats.get("last_integrated_at") or access_stats.get("last_retrieved_at")
        touch_age = self._days_since(latest_touch)
        if touch_age is not None:
            if touch_age <= 1:
                score += 0.1
            elif touch_age <= 3:
                score += 0.05

        return self._clamp(score)

    def _refresh_entry_weight(
        self,
        entry: Dict,
        bucket: Optional[str] = None,
        semantic_score: Optional[float] = None,
    ) -> Dict[str, float]:
        bucket = bucket or self._bucket_for_entry(entry)
        memory_type = self._infer_memory_type(bucket, entry=entry)
        base_importance = self._compute_base_importance(memory_type, entry)
        recency_score = self._compute_recency_score(entry)
        reinforcement_score = self._compute_reinforcement_score(entry)

        dynamic_weights = self._score_weights(include_semantic=False)
        dynamic_importance = (
            dynamic_weights["importance"] * base_importance
            + dynamic_weights["recency"] * recency_score
            + dynamic_weights["reinforcement"] * reinforcement_score
        )

        weight_profile = entry.setdefault("weight_profile", {})
        weight_profile["base_importance"] = round(base_importance, 4)
        weight_profile["recency_score"] = round(recency_score, 4)
        weight_profile["reinforcement_score"] = round(reinforcement_score, 4)
        weight_profile["dynamic_importance"] = round(dynamic_importance, 4)

        if semantic_score is not None:
            total_weights = self._score_weights(include_semantic=True)
            final_score = (
                total_weights["semantic"] * semantic_score
                + total_weights["importance"] * base_importance
                + total_weights["recency"] * recency_score
                + total_weights["reinforcement"] * reinforcement_score
            )
            weight_profile["last_score"] = round(final_score, 4)
        else:
            weight_profile.setdefault("last_score", round(dynamic_importance, 4))

        return {
            "base_importance": base_importance,
            "recency_score": recency_score,
            "reinforcement_score": reinforcement_score,
            "dynamic_importance": dynamic_importance,
            "last_score": float(weight_profile.get("last_score", dynamic_importance)),
        }

    def _refresh_all_memory_weights(self):
        for bucket, entry in self._iter_entries():
            self._refresh_entry_weight(entry, bucket=bucket)

    def _bucket_for_entry(self, target_entry: Dict) -> Optional[str]:
        for bucket, entry in self._iter_entries():
            if entry is target_entry:
                return bucket
        return None

    def _semantic_score_from_distance(self, distance: Optional[float]) -> float:
        if distance is None:
            return 0.5
        return self._clamp(1.0 - (float(distance) / 2.0))

    def _resolve_memory_text(self, memory_type: str, entry: Optional[Dict], chunk_text: str) -> str:
        if entry is None:
            return self._coerce_text(chunk_text)
        entry_text = self._coerce_text(entry.get("content", "")) or self._coerce_text(chunk_text)
        if memory_type == "generated_text":
            return self._coerce_text(chunk_text) or entry_text
        return entry_text

    def _touch_memories(self, memory_ids: List[str], event: str):
        if not memory_ids:
            return

        now_iso = datetime.now().isoformat()
        touched = set()
        for memory_id in memory_ids:
            if not memory_id or memory_id in touched:
                continue
            touched.add(memory_id)
            entry = self._entry_by_id.get(memory_id)
            if entry is None:
                continue
            self._ensure_entry_defaults(entry, self._bucket_for_entry(entry) or "texts", now_iso)
            access_stats = entry["access_stats"]
            if event == "retrieved":
                access_stats["retrieval_count"] += 1
                access_stats["last_retrieved_at"] = now_iso
            elif event == "integrated":
                access_stats["integration_count"] += 1
                access_stats["last_integrated_at"] = now_iso
            self._refresh_entry_weight(entry, semantic_score=None)

        self._save_memory_index()

    def _memory_sort_key(self, entry: Dict) -> Tuple[float, float]:
        profile = self._refresh_entry_weight(entry, semantic_score=None)
        timestamp = self._parse_timestamp(entry.get("timestamp"))
        ts_value = timestamp.timestamp() if timestamp else 0.0
        return profile["dynamic_importance"], ts_value

    def _select_priority_entries(self, entries: List[Dict], limit: int) -> List[Dict]:
        if limit <= 0 or not entries:
            return []
        ranked = sorted(entries, key=self._memory_sort_key, reverse=True)
        return ranked[:limit]

    def _memory_title(self, bucket: str, entry: Dict) -> str:
        if bucket == "characters":
            return entry.get("name") or "character"
        if bucket == "world_settings":
            return entry.get("name") or "world_setting"
        if bucket == "outlines":
            structure = entry.get("structure", {})
            kind = structure.get("kind")
            chapter = structure.get("chapter")
            if kind and chapter:
                return f"{kind}#{chapter}"
            if kind:
                return str(kind)
        if bucket == "fact_cards":
            return entry.get("card_type") or "fact_card"
        if bucket == "plot_points":
            return entry.get("position") or "plot_point"

        content = (entry.get("content") or "").strip().splitlines()
        if content:
            return content[0][:48]
        return entry.get("id", "memory")

    def get_priority_snapshot(
        self,
        topic: Optional[str] = None,
        limit: int = 5,
        include_types: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Return the highest-priority memories under the current dynamic weighting."""
        include_types = self._normalize_memory_types(include_types)
        snapshots = []

        for bucket, entry in self._iter_entries():
            if topic and entry.get("topic") != topic:
                continue
            memory_type = self._infer_memory_type(bucket, entry=entry)
            if include_types and memory_type not in include_types:
                continue

            profile = self._refresh_entry_weight(entry, bucket=bucket)
            snapshots.append(
                {
                    "id": entry.get("id"),
                    "type": memory_type,
                    "title": self._memory_title(bucket, entry),
                    "dynamic_importance": profile["dynamic_importance"],
                    "base_importance": profile["base_importance"],
                    "recency_score": profile["recency_score"],
                    "reinforcement_score": profile["reinforcement_score"],
                }
            )

        snapshots.sort(key=lambda item: item["dynamic_importance"], reverse=True)
        return snapshots[:limit]

    def store_generated_text(
        self,
        text: str,
        topic: str,
        metadata: Optional[Dict] = None,
        store_vector: bool = True,
        content_path: Optional[str] = None,
    ) -> str:
        """Store generated long-form text."""
        timestamp = datetime.now().isoformat()
        memory_id = f"text_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.memory_index['texts'])}"
        metadata = metadata or {}

        if store_vector:
            processed_docs = self.document_processor.process_document(text)
            for doc in processed_docs:
                doc["metadata"].update(
                    {
                        "type": "generated_text",
                        "memory_id": memory_id,
                        "topic": topic,
                        "timestamp": timestamp,
                        **metadata,
                    }
                )
            self.memory_store.add_documents(processed_docs)

        entry = {
            "id": memory_id,
            "topic": topic,
            "length": len(text),
            "timestamp": timestamp,
            "metadata": metadata,
            "content": text,
        }
        if content_path:
            entry["path"] = content_path

        self._ensure_entry_defaults(entry, "texts", timestamp)
        self._refresh_entry_weight(entry, bucket="texts")
        self.memory_index["texts"].append(entry)
        self._register_entry(entry)
        self._save_memory_index()
        return memory_id

    def store_outline(
        self,
        outline: str,
        topic: str,
        structure: Optional[Dict] = None,
    ) -> str:
        """Store outline-like memory."""
        timestamp = datetime.now().isoformat()
        memory_id = f"outline_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.memory_index['outlines'])}"
        structure = structure or {}

        processed_docs = self.document_processor.process_document(outline)
        for doc in processed_docs:
            doc["metadata"].update(
                {
                    "type": "outline",
                    "memory_id": memory_id,
                    "topic": topic,
                    "timestamp": timestamp,
                }
            )
        self.memory_store.add_documents(processed_docs)

        entry = {
            "id": memory_id,
            "topic": topic,
            "content": outline,
            "structure": structure,
            "timestamp": timestamp,
            "metadata": {},
        }
        self._ensure_entry_defaults(entry, "outlines", timestamp)
        self._refresh_entry_weight(entry, bucket="outlines")
        self.memory_index["outlines"].append(entry)
        self._register_entry(entry)
        self._save_memory_index()
        return memory_id

    def store_character(
        self,
        character_name: str,
        character_info: str,
        topic: str,
        attributes: Optional[Dict] = None,
    ) -> str:
        """Store character memory."""
        timestamp = datetime.now().isoformat()
        memory_id = (
            f"character_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.memory_index['characters'])}"
        )
        attributes = attributes or {}

        full_text = f"人物名称：{character_name}\n\n{character_info}"
        if attributes:
            full_text += f"\n\n人物属性：\n{json.dumps(attributes, ensure_ascii=False, indent=2)}"

        processed_docs = self.document_processor.process_document(full_text)
        for doc in processed_docs:
            doc["metadata"].update(
                {
                    "type": "character",
                    "memory_id": memory_id,
                    "character_name": character_name,
                    "topic": topic,
                    "timestamp": timestamp,
                }
            )
        self.memory_store.add_documents(processed_docs)

        entry = {
            "id": memory_id,
            "name": character_name,
            "topic": topic,
            "attributes": attributes,
            "timestamp": timestamp,
            "content": full_text,
            "metadata": {},
        }
        self._ensure_entry_defaults(entry, "characters", timestamp)
        self._refresh_entry_weight(entry, bucket="characters")
        self.memory_index["characters"].append(entry)
        self._register_entry(entry)
        self._save_memory_index()
        return memory_id

    def store_world_setting(
        self,
        setting_name: str,
        setting_info: str,
        topic: str,
    ) -> str:
        """Store world-setting memory."""
        timestamp = datetime.now().isoformat()
        memory_id = f"world_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.memory_index['world_settings'])}"

        full_text = f"世界观设定：{setting_name}\n\n{setting_info}"
        processed_docs = self.document_processor.process_document(full_text)
        for doc in processed_docs:
            doc["metadata"].update(
                {
                    "type": "world_setting",
                    "memory_id": memory_id,
                    "setting_name": setting_name,
                    "topic": topic,
                    "timestamp": timestamp,
                }
            )
        self.memory_store.add_documents(processed_docs)

        entry = {
            "id": memory_id,
            "name": setting_name,
            "topic": topic,
            "timestamp": timestamp,
            "content": full_text,
            "metadata": {},
        }
        self._ensure_entry_defaults(entry, "world_settings", timestamp)
        self._refresh_entry_weight(entry, bucket="world_settings")
        self.memory_index["world_settings"].append(entry)
        self._register_entry(entry)
        self._save_memory_index()
        return memory_id

    def store_plot_point(
        self,
        plot_point: str,
        topic: str,
        position: Optional[str] = None,
    ) -> str:
        """Store plot-point memory."""
        timestamp = datetime.now().isoformat()
        memory_id = f"plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.memory_index['plot_points'])}"
        position = position or "unknown"

        processed_docs = self.document_processor.process_document(plot_point)
        for doc in processed_docs:
            doc["metadata"].update(
                {
                    "type": "plot_point",
                    "memory_id": memory_id,
                    "topic": topic,
                    "position": position,
                    "timestamp": timestamp,
                }
            )
        self.memory_store.add_documents(processed_docs)

        entry = {
            "id": memory_id,
            "topic": topic,
            "position": position,
            "timestamp": timestamp,
            "content": plot_point,
            "metadata": {},
        }
        self._ensure_entry_defaults(entry, "plot_points", timestamp)
        self._refresh_entry_weight(entry, bucket="plot_points")
        self.memory_index["plot_points"].append(entry)
        self._register_entry(entry)
        self._save_memory_index()
        return memory_id

    def store_fact_card(
        self,
        card_text: str,
        topic: str,
        card_type: str = "general",
        metadata: Optional[Dict] = None,
    ) -> str:
        """Store short fact-card memory used as lightweight constraints."""
        timestamp = datetime.now().isoformat()
        memory_id = (
            f"fact_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.memory_index.get('fact_cards', []))}"
        )
        metadata = metadata or {}

        processed_docs = self.document_processor.process_document(card_text)
        for doc in processed_docs:
            doc["metadata"].update(
                {
                    "type": "fact_card",
                    "memory_id": memory_id,
                    "topic": topic,
                    "card_type": card_type,
                    "timestamp": timestamp,
                    **metadata,
                }
            )
        self.memory_store.add_documents(processed_docs)

        entry = {
            "id": memory_id,
            "topic": topic,
            "card_type": card_type,
            "content": card_text,
            "timestamp": timestamp,
            "metadata": metadata,
        }
        self._ensure_entry_defaults(entry, "fact_cards", timestamp)
        self._refresh_entry_weight(entry, bucket="fact_cards")
        self.memory_index.setdefault("fact_cards", []).append(entry)
        self._register_entry(entry)
        self._save_memory_index()
        return memory_id

    def get_recent_outlines(
        self,
        topic: str,
        limit: int = 3,
        kind: Optional[str] = None,
    ) -> List[Dict]:
        """Get the most recent outlines by write order."""
        outlines = [o for o in self.memory_index.get("outlines", []) if o.get("topic") == topic]
        if kind is not None:
            outlines = [o for o in outlines if o.get("structure", {}).get("kind") == kind]
        return outlines[-limit:] if limit > 0 else outlines

    def get_recent_fact_cards(self, topic: str, limit: int = 10) -> List[Dict]:
        """Get the most recent fact cards by write order."""
        cards = [c for c in self.memory_index.get("fact_cards", []) if c.get("topic") == topic]
        return cards[-limit:] if limit > 0 else cards

    def retrieve_memories(
        self,
        query: str,
        memory_types: Optional[List[str]] = None,
        topic: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Retrieve memories with semantic search plus dynamic importance reranking.
        """
        normalized_types = self._normalize_memory_types(memory_types)
        current_chapter = self._extract_current_chapter(query)
        needs = self._analyze_context_needs(query, current_chapter)
        focus_corpus = self._build_focus_corpus(topic or "", current_chapter, query)
        total_weights = self._score_weights(include_semantic=True)
        dynamic_weights = self._score_weights(include_semantic=False)

        if self.document_processor.embedding_model is None:
            ranked = []
            for bucket, entry in self._iter_candidate_entries(topic, normalized_types, current_chapter):
                memory_type = self._infer_memory_type(bucket, entry=entry)
                text = self._resolve_memory_text(memory_type, entry, entry.get("content", ""))
                keyword_score = self._keyword_score(query, text)
                components = self._refresh_entry_weight(entry, bucket=bucket, semantic_score=keyword_score)
                chapter_factor = self._chapter_distance_weight(bucket, entry, current_chapter)
                anchor_bonus = float(getattr(self.config, "memory_anchor_bonus", 0.18))
                horizon = self._memory_horizon(bucket, entry)
                anchor_score = anchor_bonus if horizon == "anchor" else 0.0
                need_boost = self._memory_need_boost(bucket, entry, needs)
                entity_name = entry.get("name") or entry.get("metadata", {}).get("character_name") or entry.get("metadata", {}).get("setting_name")
                entity_focus = 1.0
                if memory_type in {"character", "world_setting"}:
                    entity_focus = 0.45 + self._entity_focus_score(str(entity_name or ""), focus_corpus)
                final_score = (
                    total_weights["semantic"] * keyword_score
                    + total_weights["importance"] * components["base_importance"]
                    + total_weights["recency"] * components["recency_score"]
                    + total_weights["reinforcement"] * components["reinforcement_score"]
                    + anchor_score
                ) * chapter_factor * need_boost * entity_focus
                ranked.append(
                    {
                        "id": entry.get("id"),
                        "text": text,
                        "metadata": {"type": memory_type, **(entry.get("metadata", {}) or {})},
                        "distance": None,
                        "semantic_score": round(keyword_score, 4),
                        "base_importance": round(components["base_importance"], 4),
                        "recency_score": round(components["recency_score"], 4),
                        "reinforcement_score": round(components["reinforcement_score"], 4),
                        "dynamic_importance": round(components["dynamic_importance"], 4),
                        "final_score": round(final_score, 4),
                    }
                )
            ranked.sort(key=lambda item: item["final_score"], reverse=True)
            ranked = ranked[:top_k]
            self._touch_memories(
                [item["id"] for item in ranked if item["id"] in self._entry_by_id],
                event="retrieved",
            )
            return ranked

        filter_metadata = {}
        if normalized_types:
            filter_metadata["type"] = {"$in": normalized_types}
        if topic:
            filter_metadata["topic"] = topic

        query_embedding = self.document_processor.get_embeddings([query])[0]
        oversample = max(1, int(getattr(self.config, "memory_retrieval_oversample_factor", 4)))
        raw_top_k = max(top_k, top_k * oversample)

        results = self.memory_store.search(
            query_embedding.tolist(),
            top_k=raw_top_k,
            filter_metadata=filter_metadata if filter_metadata else None,
        )

        merged_results: Dict[str, Dict] = {}
        ordered_fallback_results: List[Dict] = []

        for index, result in enumerate(results):
            metadata = result.get("metadata", {}) or {}
            memory_id = metadata.get("memory_id")
            entry = self._entry_by_id.get(memory_id) if memory_id else None
            memory_type = self._infer_memory_type(
                self._bucket_for_entry(entry) if entry else None,
                entry=entry,
                metadata=metadata,
            )
            semantic_score = self._semantic_score_from_distance(result.get("distance"))

            if entry is not None:
                components = self._refresh_entry_weight(entry, semantic_score=semantic_score)
                base_importance = components["base_importance"]
                recency_score = components["recency_score"]
                reinforcement_score = components["reinforcement_score"]
                dynamic_importance = components["dynamic_importance"]
                text = self._resolve_memory_text(memory_type, entry, result.get("text", ""))
                merged_metadata = dict(entry.get("metadata", {}) or {})
                merged_metadata.update(metadata)
                merged_metadata.setdefault("type", memory_type)
                result_id = memory_id
                bucket = self._bucket_for_entry(entry) or "texts"
                chapter_factor = self._chapter_distance_weight(bucket, entry, current_chapter)
                anchor_score = float(getattr(self.config, "memory_anchor_bonus", 0.18)) if self._memory_horizon(bucket, entry) == "anchor" else 0.0
                need_boost = self._memory_need_boost(bucket, entry, needs)
            else:
                base_importance = self.TYPE_BASE_WEIGHTS.get(memory_type, 0.58)
                recency_score = 0.5
                reinforcement_score = 0.0
                dynamic_importance = (
                    dynamic_weights["importance"] * base_importance
                    + dynamic_weights["recency"] * recency_score
                    + dynamic_weights["reinforcement"] * reinforcement_score
                )
                text = result.get("text", "")
                merged_metadata = metadata
                result_id = f"vector_result_{index}"
                chapter_factor = 1.0
                anchor_score = 0.0
                need_boost = 1.0

            final_score = (
                total_weights["semantic"] * semantic_score
                + total_weights["importance"] * base_importance
                + total_weights["recency"] * recency_score
                + total_weights["reinforcement"] * reinforcement_score
                + anchor_score
            ) * chapter_factor * need_boost

            payload = {
                "id": result_id,
                "text": text,
                "metadata": merged_metadata,
                "distance": result.get("distance"),
                "semantic_score": round(semantic_score, 4),
                "base_importance": round(base_importance, 4),
                "recency_score": round(recency_score, 4),
                "reinforcement_score": round(reinforcement_score, 4),
                "dynamic_importance": round(dynamic_importance, 4),
                "final_score": round(final_score, 4),
            }

            if memory_id:
                prev = merged_results.get(memory_id)
                if prev is None or payload["final_score"] > prev["final_score"]:
                    merged_results[memory_id] = payload
            else:
                ordered_fallback_results.append(payload)

        ranked = list(merged_results.values()) + ordered_fallback_results
        ranked.sort(key=lambda item: item["final_score"], reverse=True)
        ranked = ranked[:top_k]

        self._touch_memories(
            [item["id"] for item in ranked if item["id"] in self._entry_by_id],
            event="retrieved",
        )
        return ranked

    def get_characters_by_topic(self, topic: str) -> List[Dict]:
        """Get all character memories for the topic."""
        return [char for char in self.memory_index["characters"] if char.get("topic") == topic]

    def get_outline_by_topic(self, topic: str) -> Optional[Dict]:
        """Get the most relevant outline for the topic, preferring global outline."""
        outlines = [outline for outline in self.memory_index["outlines"] if outline.get("topic") == topic]
        if not outlines:
            return None
        global_outlines = [
            outline for outline in outlines if outline.get("structure", {}).get("kind") == "global_outline"
        ]
        if global_outlines:
            return global_outlines[-1]
        return outlines[-1]

    def get_relevant_context(
        self,
        query: str,
        topic: str,
        include_types: Optional[List[str]] = None,
    ) -> str:
        """
        Build the context injected into prompts using weighted memory integration.
        """
        include_types = self._normalize_memory_types(include_types)
        if include_types is None:
            include_types = ["outline", "plot_point", "fact_card"]
        current_chapter = self._extract_current_chapter(query)
        needs = self._analyze_context_needs(query, current_chapter)
        focus_corpus = self._build_focus_corpus(topic, current_chapter, query)
        context_budget = max(1200, int(getattr(self.config, "memory_context_char_budget", 5000)))

        def append_block(blocks: List[str], heading: str, items: List[str]) -> None:
            if not items:
                return
            candidate = [heading] + items
            candidate_text = "\n".join(candidate)
            current_size = len("\n".join(blocks))
            if current_size + len(candidate_text) > context_budget:
                remain = max(0, context_budget - current_size - len(heading) - 1)
                trimmed: List[str] = []
                used = 0
                for item in items:
                    if used >= remain:
                        break
                    take = item[: max(0, remain - used)]
                    if not take:
                        break
                    trimmed.append(take)
                    used += len(take) + 1
                if not trimmed:
                    return
                candidate = [heading] + trimmed
            blocks.append("\n".join(candidate))

        context_parts: List[str] = []
        integrated_ids: List[str] = []

        anchor_parts: List[str] = []
        rolling_candidates = self.get_recent_outlines(topic, limit=3, kind="rolling_summary")
        rolling = self._select_priority_entries(rolling_candidates, limit=1)
        if rolling and rolling[0].get("content"):
            anchor_parts.append(rolling[0]["content"])
            integrated_ids.append(rolling[0]["id"])

        global_outline = self.get_outline_by_topic(topic)
        if global_outline and global_outline.get("structure", {}).get("kind") == "global_outline":
            anchor_parts.append(global_outline.get("content", "")[:1200])
            integrated_ids.append(global_outline["id"])
        append_block(context_parts, "=== 长期锚点 ===", [p for p in anchor_parts if p])

        chapter_outline_items: List[str] = []
        if current_chapter is not None:
            outlines = [
                o for o in self.memory_index.get("outlines", [])
                if o.get("topic") == topic
                and o.get("structure", {}).get("kind") in {"chapter_outline", "chapter_plan"}
                and o.get("structure", {}).get("chapter") == current_chapter
            ]
            ranked_outlines = self._select_priority_entries(outlines, limit=2)
            for item in ranked_outlines:
                if item.get("content"):
                    chapter_outline_items.append(item["content"])
                    integrated_ids.append(item["id"])
        append_block(context_parts, "=== 当前章任务 ===", chapter_outline_items)

        recent_chapters = self.get_recent_outlines(topic, limit=6, kind="chapter_summary")
        recent_chapters = [
            ch for ch in recent_chapters
            if self._chapter_distance_weight("outlines", ch, current_chapter) > 0
        ]
        chapter_summaries = self._select_priority_entries(
            recent_chapters,
            limit=2 + (1 if needs.get("summary", 1.0) >= 1.3 else 0),
        )
        chapter_summary_items = []
        for chapter in chapter_summaries:
            if chapter.get("content"):
                chapter_summary_items.append(chapter["content"])
                integrated_ids.append(chapter["id"])
        append_block(context_parts, "=== 近邻章节摘要 ===", chapter_summary_items)

        recent_cards = self.get_recent_fact_cards(topic, limit=12)
        recent_cards = [
            card for card in recent_cards
            if self._chapter_distance_weight("fact_cards", card, current_chapter) > 0
        ]
        high_priority_cards = self._select_priority_entries(
            recent_cards,
            limit=4 + (1 if needs.get("fact", 1.0) >= 1.25 else 0),
        )
        fact_items = []
        for card in high_priority_cards:
            if card.get("content"):
                fact_items.append(card["content"])
                integrated_ids.append(card["id"])
        append_block(context_parts, "=== 高价值事实约束 ===", fact_items)

        memories = self.retrieve_memories(
            query,
            memory_types=include_types,
            topic=topic,
            top_k=12,
        )

        characters = [m for m in memories if m.get("metadata", {}).get("type") == "character"]
        if characters:
            char_items = []
            seen_names = set()
            characters = sorted(
                characters,
                key=lambda item: self._entity_focus_score(
                    str(item.get("metadata", {}).get("character_name", "")),
                    focus_corpus,
                ),
                reverse=True,
            )
            for char in characters:
                name = char.get("metadata", {}).get("character_name", "未知")
                if name not in seen_names:
                    focus_score = self._entity_focus_score(str(name), focus_corpus)
                    if focus_score <= 0 and len(char_items) >= 1:
                        continue
                    char_items.append(char["text"])
                    seen_names.add(name)
                    if char["id"] in self._entry_by_id:
                        integrated_ids.append(char["id"])
            char_limit = 2 + (1 if needs.get("character", 1.0) >= 1.25 else 0)
            append_block(context_parts, "=== 长期人物锚点 ===", char_items[:char_limit])

        outlines = [m for m in memories if m.get("metadata", {}).get("type") == "outline"]
        if outlines:
            outline_items = []
            for outline in outlines[:2]:
                outline_items.append(outline["text"])
                if outline["id"] in self._entry_by_id:
                    integrated_ids.append(outline["id"])
            outline_limit = 1 + (1 if max(needs.get("summary", 1.0), needs.get("plot", 1.0)) >= 1.2 else 0)
            append_block(context_parts, "=== 补充大纲约束 ===", outline_items[:outline_limit])

        world_settings = [m for m in memories if m.get("metadata", {}).get("type") == "world_setting"]
        if world_settings:
            world_items = []
            world_settings = sorted(
                world_settings,
                key=lambda item: self._entity_focus_score(
                    str(item.get("metadata", {}).get("setting_name", item.get("text", "")[:24])),
                    focus_corpus,
                ),
                reverse=True,
            )
            for setting in world_settings:
                setting_name = str(item_name) if (item_name := setting.get("metadata", {}).get("setting_name")) else ""
                focus_score = self._entity_focus_score(setting_name, focus_corpus) if setting_name else 0.0
                if focus_score <= 0 and len(world_items) >= 1:
                    continue
                world_items.append(setting["text"])
                if setting["id"] in self._entry_by_id:
                    integrated_ids.append(setting["id"])
            world_limit = 1 + (1 if needs.get("world", 1.0) >= 1.2 else 0)
            append_block(context_parts, "=== 长期世界规则 ===", world_items[:world_limit])

        plot_points = [m for m in memories if m.get("metadata", {}).get("type") == "plot_point"]
        if plot_points:
            plot_items = []
            for plot in plot_points[:3]:
                plot_items.append(plot["text"])
                if plot["id"] in self._entry_by_id:
                    integrated_ids.append(plot["id"])
            plot_limit = 2 + (1 if needs.get("plot", 1.0) >= 1.25 else 0)
            append_block(context_parts, "=== 近邻情节要点 ===", plot_items[:plot_limit])

        fact_cards = [m for m in memories if m.get("metadata", {}).get("type") == "fact_card"]
        if fact_cards:
            fact_card_items = []
            for card in fact_cards[:5]:
                fact_card_items.append(card["text"])
                if card["id"] in self._entry_by_id:
                    integrated_ids.append(card["id"])
            fact_limit = 3 + (1 if needs.get("fact", 1.0) >= 1.25 else 0)
            append_block(context_parts, "=== 补充事实卡片 ===", fact_card_items[:fact_limit])

        self._touch_memories(integrated_ids, event="integrated")
        return "\n".join(context_parts) if context_parts else ""
