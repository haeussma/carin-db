from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

import numpy as np
import pandas as pd

from backend.spreadsheet import load_sheets

from .model import (
    CaseMode,
    GraphSheetModel,
    MultiSpec,
    RefProperty,
    SheetNode,
    ValueProperty,
)


@dataclass(frozen=True)
class NodeRef:
    """Reference to a node either by key (for MERGE) or by a temp_id (create-only)."""

    key: dict[str, Any] | None = None
    temp_id: str | None = None


@dataclass(frozen=True)
class UpsertNode:
    label: str
    ref: NodeRef
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UpsertEdge:
    src_label: str
    src_ref: NodeRef
    rel_type: str
    dst_label: str
    dst_ref: NodeRef
    unique: bool = True
    properties: dict[str, Any] = field(default_factory=dict)
    require_existing_dst: bool = True  # executor must MATCH destination


# ---------- Planner ----------


class UpsertPlanner:
    """
    Build a DB-agnostic upsert plan from a GraphSheetModel + DataFrames.

    - Nodes: MERGE when a unique key is present; otherwise create-only (tagged via temp_id).
    - Edges: emitted with destination referenced by key; no auto-creation. Existence is
      optionally validated against the current batch, and MUST be enforced at upsert time.
    """

    def __init__(
        self,
        model: GraphSheetModel,
        sheets_data: dict[str, pd.DataFrame],
        *,
        validate_refs_in_batch: bool = False,  # False → defer checks to executor
        on_missing_ref: Literal["error", "skip"] = "error",  # batch-only behavior
    ):
        self.model = model
        self.sheets_data = sheets_data
        self.validate_refs_in_batch = validate_refs_in_batch
        self.on_missing_ref = on_missing_ref

        self.sheet_by: dict[str, SheetNode] = {s.name: s for s in model.sheets}
        self.target_unique: dict[str, str | None] = {}
        self.batch_raw: dict[tuple[str, str], set[Any]] = {}
        self.batch_low: dict[tuple[str, str], set[Any]] = {}

        self.nodes: list[UpsertNode] = []
        self.edges: list[UpsertEdge] = []
        self._seen_nodes: set[tuple] = set()
        self._seen_edges: set[tuple] = set()

        # --- Project hub (NEW) ---
        self._project_ref = NodeRef(key={"name": model.project_name})
        self._project_props: dict[str, Any] = {
            "name": model.project_name,
            "created_at": getattr(model, "created_at", None),
            "last_modified": getattr(model, "last_modified", None),
        }
        # remove Nones (optional)
        self._project_props = {
            k: v for k, v in self._project_props.items() if v is not None
        }
        # --------------------------

    def plan(self) -> tuple[list[UpsertNode], list[UpsertEdge]]:
        self._validate_inputs()
        self._validate_refs_point_to_unique()
        self._build_batch_indexes()

        # Ensure the Project node is included (NEW)
        self._emit_project_node()

        self._emit_all()
        return self.nodes, self.edges

    def _emit_project_node(self) -> None:
        sig = ("Project", tuple(sorted(self._project_ref.key.items())))
        if sig not in self._seen_nodes:
            self.nodes.append(
                UpsertNode("Project", self._project_ref, self._project_props)
            )
            self._seen_nodes.add(sig)

    def _emit_all(self) -> None:
        for sname, df in self.sheets_data.items():
            sheet = self.sheet_by[sname]
            uniq = self._unique_or_none(sheet)
            for i, row in df.iterrows():
                src_ref = self._make_src_ref(sname, uniq, i, row)
                self._emit_node(sname, src_ref, sheet, row)
                # link every node to Project (NEW)
                self._emit_project_edge(sname, src_ref)
                self._emit_refs(sname, src_ref, sheet, row)

    def _emit_project_edge(self, sname: str, src_ref: NodeRef) -> None:
        # build a dedup signature for this edge
        esig = (
            self._node_sig(sname, src_ref),
            "IN_PROJECT",
            "Project",
            (("name", self.model.project_name),),
        )
        if esig in self._seen_edges:
            return
        self.edges.append(
            UpsertEdge(
                src_label=sname,
                src_ref=src_ref,  # uses key or temp_id
                rel_type="IN_PROJECT",
                dst_label="Project",
                dst_ref=self._project_ref,  # matches Project by {name}
                unique=True,  # MERGE relationship (no dup)
                properties={},
                require_existing_dst=True,
            )
        )
        self._seen_edges.add(esig)

    # --- Phase 0: validation ---

    def _validate_inputs(self) -> None:
        missing = [k for k in self.sheet_by if k not in self.sheets_data]
        if missing:
            # raise your own SheetNameError if preferred
            raise ValueError(f"Missing sheets in data: {missing}")

    def _validate_refs_point_to_unique(self) -> None:
        # cache each sheet's unique key name (or None)
        for s in self.model.sheets:
            u = self._unique_or_none(s)
            self.target_unique[s.name] = u.name if u else None
        # each RefProperty must target the unique key of its target sheet
        for s in self.model.sheets:
            for rp in self._ref_props(s):
                uk = self.target_unique.get(rp.to)
                if uk is None or uk != rp.on:
                    raise ValueError(
                        f"Ref '{s.name}.{rp.name}' → '{rp.to}.{rp.on}' but unique of '{rp.to}' is '{uk}'"
                    )

    def _build_batch_indexes(self) -> None:
        for sname, df in self.sheets_data.items():
            sheet = self.sheet_by[sname]
            for vp in self._value_props(sheet):
                vals = set(self._iter_non_nan(df.get(vp.name)))
                self.batch_raw[(sname, vp.name)] = vals
                self.batch_low[(sname, vp.name)] = {
                    v.lower() if isinstance(v, str) else v for v in vals
                }

    def _make_src_ref(
        self, sname: str, uniq: ValueProperty | None, idx: int, row: pd.Series
    ) -> NodeRef:
        if uniq is None:
            return NodeRef(temp_id=str(uuid.uuid4()))
        v = self._coerce(row.get(uniq.name))
        return (
            NodeRef(key={uniq.name: v})
            if not self._is_nan(v)
            else NodeRef(temp_id=str(uuid.uuid4()))
        )

    def _emit_node(
        self, sname: str, ref: NodeRef, sheet: SheetNode, row: pd.Series
    ) -> None:
        props = {
            vp.name: self._coerce(row.get(vp.name))
            for vp in self._value_props(sheet)
            if not self._is_nan(row.get(vp.name))
        }
        sig = self._node_sig(sname, ref)
        if sig not in self._seen_nodes:
            self.nodes.append(UpsertNode(sname, ref, props))
            self._seen_nodes.add(sig)

    def _emit_refs(
        self, sname: str, src_ref: NodeRef, sheet: SheetNode, row: pd.Series
    ) -> None:
        for rp in self._ref_props(sheet):
            cell = row.get(rp.name)
            if self._is_nan(cell):
                continue
            for tok in self._split(cell, rp.multi):
                t_raw = str(tok)
                t_norm = t_raw if rp.case == CaseMode.SENSITIVE else t_raw.lower()

                if self.validate_refs_in_batch and not self._exists_in_batch(
                    rp, t_norm
                ):
                    if self.on_missing_ref == "skip":
                        continue
                    raise ValueError(
                        f"Missing target in batch for ref '{sname}.{rp.name}' token '{t_raw}' → '{rp.to}.{rp.on}'"
                    )

                dst_ref = NodeRef(
                    key={rp.on: (t_norm if rp.case == CaseMode.INSENSITIVE else t_raw)}
                )
                self._emit_edge(sname, src_ref, rp, dst_ref)

    def _exists_in_batch(self, rp: RefProperty, norm_val: Any) -> bool:
        batch = self.batch_low if rp.case == CaseMode.INSENSITIVE else self.batch_raw
        return norm_val in batch.get((rp.to, rp.on), set())

    def _emit_edge(
        self, sname: str, src_ref: NodeRef, rp: RefProperty, dst_ref: NodeRef
    ) -> None:
        esig = (
            self._node_sig(sname, src_ref),
            rp.edge,
            rp.to,
            tuple(sorted(dst_ref.key.items())),
        )
        if esig in self._seen_edges:
            return
        self.edges.append(
            UpsertEdge(
                src_label=sname,
                src_ref=src_ref,
                rel_type=rp.edge,
                dst_label=rp.to,
                dst_ref=dst_ref,
                unique=bool(rp.unique),
                properties={},
                require_existing_dst=True,
            )
        )
        self._seen_edges.add(esig)

    # --- Helpers ---

    @staticmethod
    def _value_props(sheet: SheetNode) -> list[ValueProperty]:
        return [p for p in sheet.properties if isinstance(p, ValueProperty)]

    @staticmethod
    def _ref_props(sheet: SheetNode) -> list[RefProperty]:
        return [p for p in sheet.properties if isinstance(p, RefProperty)]

    @staticmethod
    def _unique_or_none(sheet: SheetNode) -> ValueProperty | None:
        ups = [p for p in UpsertPlanner._value_props(sheet) if p.unique]
        if not ups:
            return None
        if len(ups) > 1:
            raise ValueError(
                f"Sheet '{sheet.name}' has multiple unique props: {[p.name for p in ups]}"
            )
        return ups[0]

    @staticmethod
    def _iter_non_nan(series: pd.Series | None) -> Iterable[Any]:
        if series is None:
            return []
        for v in series:
            if not UpsertPlanner._is_nan(v):
                yield UpsertPlanner._coerce(v)

    @staticmethod
    def _split(v: Any, mspec: MultiSpec | None) -> list[str]:
        s = "" if v is None else str(v)
        if mspec is None:
            s = s.strip()
            return [s] if s else []
        parts = s.split(mspec.sep)
        if mspec.trim:
            parts = [p.strip() for p in parts]
        if not mspec.allow_empty:
            parts = [p for p in parts if p != ""]
        return parts

    @staticmethod
    def _coerce(v: Any) -> Any:
        if isinstance(v, pd.Timestamp):
            return v.to_pydatetime()
        if isinstance(v, np.generic):
            return v.item()
        return v

    @staticmethod
    def _is_nan(v: Any) -> bool:
        if v is None:
            return True
        if isinstance(v, float) and np.isnan(v):
            return True
        return False

    @staticmethod
    def _node_sig(label: str, ref: NodeRef) -> tuple:
        if ref.key:
            return (label, tuple(sorted(ref.key.items())))
        return (label, "__CREATE_ONLY__", ref.temp_id)


if __name__ == "__main__":
    from rich import print

    sheets = load_sheets("test_data/genoscope/Genoscope_reaction4.xlsx")

    with open("test_model.json", "r") as f:
        project = GraphSheetModel.model_validate_json(f.read())

    planner = UpsertPlanner(project, sheets)
    nodes, edges = planner.plan()
    print(nodes[-10:])
    print(edges[-10:])
    # print(project)
