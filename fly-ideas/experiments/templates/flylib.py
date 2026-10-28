#!/usr/bin/env python3
"""Общая библиотека загрузки коннектомов (FlyWire v783 и MaleCNS v1.0), LIF-симуляции и графиков.

Используется готовыми скриптами анализа 10..19, чтобы не тратить API на однотипный код чтения
таблиц, приведения знаков нейромедиаторов и расчёта спайковой динамики Shiu et al. 2024.
Поддерживает реальные файлы из папки FLY_DATA и мгновенный синтетический режим (--synth) с той же
схемой колонок.
"""
from __future__ import annotations

import json
import math
import os
import pickle
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import sparse

DATA = Path(os.environ.get("FLY_DATA", "workspace/data"))
RUN = Path(os.environ.get("FLY_RUN_DIR", "."))
SCRIPTS = Path(os.environ.get("FLY_SCRIPTS", str(Path(__file__).resolve().parent)))

# Сдержанная палитра приложения (стиль Bklit, без неона, радуги и чистого белого)
PALETTE = {
    "steel": "#3f5f8a",
    "olive": "#6b7f4a",
    "ochre": "#a8792f",
    "brick": "#8a4b4b",
    "umber": "#7d5a3c",
    "slate": "#5a626a",
    "stone": "#c9c2b8",
    "ink": "#3c3833",
    "muted": "#6b655e",
    "paper": "#f6f3ee",
}
SERIES_COLORS = ["#3f5f8a", "#6b7f4a", "#a8792f", "#8a4b4b", "#5a626a", "#7d5a3c"]

# Проверенные root_id из эталонного ноутбука Shiu et al. 2024 (FlyWire v783)
SHIU_V783_SETS: Dict[str, List[int]] = {
    "sugar_GRNs": [
        720575940616885538, 720575940630233916, 720575940639332736, 720575940632889389,
        720575940617000768, 720575940632425919, 720575940637568838, 720575940629176663,
        720575940621502051, 720575940638202345, 720575940612670570, 720575940611875570,
        720575940621754367, 720575940633143833, 720575940613601698, 720575940630797113,
        720575940639198653, 720575940639259967, 720575940624963786, 720575940640649691,
        720575940610788069, 720575940623172843, 720575940628853239,
    ],
    "bitter_GRNs": [
        720575940619072513, 720575940646212996, 720575940622298631, 720575940642088333,
        720575940627692048, 720575940617239197, 720575940618682526, 720575940604714528,
        720575940603266592, 720575940604027168, 720575940619197093, 720575940610259370,
    ],
    "JO_auditory": [
        720575940645106376, 720575940615272415, 720575940619869120, 720575940620257345,
        720575940620382889, 720575940630834683, 720575940632449619, 720575940634020508,
        720575940606154370, 720575940605919334, 720575940608884931, 720575940616655989,
    ],
    "LC4_looming": [
        720575940605598892, 720575940611134833, 720575940612580977, 720575940613256863,
        720575940613260959, 720575940614914107, 720575940615462587, 720575940617176321,
        720575940617266722, 720575940618807105, 720575940620795728, 720575940622108001,
    ],
    "Or56a_olfactory": [
        720575940659222657, 720575940641403021, 720575940624211470, 720575940616536209,
        720575940615427734, 720575940628380827, 720575940654069409, 720575940613671330,
        720575940644590116, 720575940612972328, 720575940627318696, 720575940627805096,
    ],
    "MN9_feeding": [720575940660219265, 720575940618238523],
    "aDN1_grooming": [720575940616185531, 720575940624319124],
    "DNa_turning": [720575940627787609, 720575940644438551, 720575940629327659, 720575940604737708],
    "P9_forward": [720575940626730883, 720575940620300308, 720575940627652358, 720575940635872101],
    "MDN_escape": [720575940616026939, 720575940631082808, 720575940640331472, 720575940610236514],
    "GF_escape": [720575940622838154, 720575940632499757],
}

SHIU_DEFAULTS = dict(
    v_0=-52.0,
    v_rst=-52.0,
    v_th=-45.0,
    t_mbr=20.0,
    tau_g=5.0,
    t_rfc=2.2,
    t_dly=1.8,
    w_syn=0.275,
    f_poi=250.0,
)


def setup_plot_style():
    """Единое сдержанное оформление графиков под палитру приложения."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    plt.rcParams.update({
        "font.size": 9,
        "axes.titlesize": 9.5,
        "axes.labelsize": 8.5,
        "axes.edgecolor": "#9a938a",
        "axes.linewidth": 0.7,
        "axes.labelcolor": PALETTE["ink"],
        "text.color": PALETTE["ink"],
        "xtick.color": PALETTE["muted"],
        "ytick.color": PALETTE["muted"],
        "figure.facecolor": PALETTE["paper"],
        "axes.facecolor": PALETTE["paper"],
        "savefig.facecolor": PALETTE["paper"],
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.color": "#ded8ce",
        "grid.linewidth": 0.5,
    })
    seq_cmap = LinearSegmentedColormap.from_list(
        "bklit_seq", ["#efeae1", "#d3c6b1", "#a8792f", "#8a4b4b", "#3c3833"]
    )
    div_cmap = LinearSegmentedColormap.from_list(
        "bklit_div", ["#3f5f8a", "#9fb0c2", "#efeae1", "#c99b7c", "#8a4b4b"]
    )
    return plt, seq_cmap, div_cmap


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def nt_to_sign(nt_series: pd.Series) -> np.ndarray:
    """Знак синапса по предсказанному нейромедиатору (Eckstein et al. 2024, Shiu et al. 2024)."""
    vals = nt_series.fillna("acetylcholine").astype(str).str.lower()
    neg = vals.str.contains("gaba|glut|glyc|inhib")
    return np.where(neg, -1.0, 1.0)


def infer_region(cell_type: str, cell_class: str = "", super_class: str = "") -> str:
    """Приписывает нейрон к крупной функциональной области для анализа лезий и контуров."""
    t = f"{cell_type} {cell_class} {super_class}".upper()
    if any(k in t for k in ("KC", "MBON", "APL", "DPM", "PPL1", "PAM", "MUSHROOM")):
        return "MB"
    if any(k in t for k in ("EPG", "PEN", "PEG", "DELTA7", "FB", "EB", "PB", "CENTRAL_COMPLEX", "CX")):
        return "CX"
    if any(k in t for k in ("GNG", "SEZ", "GRN", "MN9", "FDG", "GUST")):
        return "GNG_SEZ"
    if any(k in t for k in ("AVLP", "WED", "AMMC", "JO", "VPN1", "AUDIT")):
        return "AVLP_WED"
    if any(k in t for k in ("LH", "LATERAL_HORN", "LHN")):
        return "LH"
    if any(k in t for k in ("AL", "ORN", "OR56", "OR67", "PN", "ANTENNAL")):
        return "AL"
    if any(k in t for k in ("LC", "LPLC", "OPTIC", "ME", "LO", "LP", "VISUAL")):
        return "OPTIC"
    if any(k in t for k in ("DN", "MDN", "GF", "GIANT", "P9", "DESCEND")):
        return "DN_MOTOR"
    if any(k in t for k in ("MN", "MOTOR", "VNC")):
        return "VNC_MOTOR"
    return "CENTRAL_OTHER"


def build_synthetic_connectome(
    n_scale: float = 1.0,
    seed: int = 0,
    male: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    """Строит модульный синтетический коннектом с реальными классами клеток и путями.

    Сохраняет биологическую логику связей:
      - вкусовой путь: sugar_GRN -> GNG_SEZ -> MN_feed (и торможение от bitter_GRN);
      - механо/слуховой путь: JO -> AMMC -> AVLP_WED -> vPN1 -> pC1 / aDN1;
      - зрительный путь: LC_VPN -> OPTIC/AVLP -> GF/MDN (побег) и слабый вход в MB/DAN (Vogt 2016);
      - обонятельный и MB-контур: PN -> KC <-> APL, KC -> MBON_app / MBON_avo, PPL1 / PAM;
      - нисходящий и моторный выход: MBON / LH / CX / pC1 -> DN -> VNC_MN (ходьба, поворот, стоп, крыло).
    """
    rng = np.random.default_rng(seed)
    s = max(0.35, float(n_scale))
    specs = [
        ("sugar_GRN", int(24 * s), "GNG_SEZ", +1.0, "isomorphic"),
        ("bitter_GRN", int(24 * s), "GNG_SEZ", +1.0, "isomorphic"),
        ("JO", int(36 * s), "AVLP_WED", +1.0, "isomorphic"),
        ("AMMC_B1", int(40 * s), "AVLP_WED", +1.0, "isomorphic"),
        ("AMMC_inh", int(20 * s), "AVLP_WED", -1.0, "isomorphic"),
        ("WED_VLP", int(44 * s), "AVLP_WED", +1.0, "isomorphic"),
        ("vPN1", int(20 * s), "AVLP_WED", +1.0, "dimorphic"),
        ("pC1", int(18 * s), "CENTRAL_OTHER", +1.0, "dimorphic"),
        ("P1", int(14 * s) if male else int(4 * s), "CENTRAL_OTHER", +1.0, "male-specific" if male else "female-specific"),
        ("aSP13_PAM", int(16 * s), "MB", +1.0, "dimorphic"),
        ("LC_VPN", int(24 * s), "OPTIC", +1.0, "isomorphic"),
        ("LPLC_loom", int(30 * s), "OPTIC", +1.0, "isomorphic"),
        ("PN", int(90 * s), "AL", +1.0, "isomorphic"),
        ("Or67d_PN", int(18 * s), "AL", +1.0, "dimorphic"),
        ("KCg", int(260 * s), "MB", +1.0, "isomorphic"),
        ("KCab", int(140 * s), "MB", +1.0, "isomorphic"),
        ("APL", max(4, int(6 * s)), "MB", -1.0, "isomorphic"),
        ("MBON_app", max(8, int(14 * s)), "MB", +1.0, "isomorphic"),
        ("MBON_avo", max(8, int(14 * s)), "MB", +1.0, "isomorphic"),
        ("PPL1", max(8, int(14 * s)), "MB", +1.0, "isomorphic"),
        ("PAM", max(10, int(18 * s)), "MB", +1.0, "isomorphic"),
        ("GNG_relay", int(70 * s), "GNG_SEZ", +1.0, "isomorphic"),
        ("GNG_inh", int(28 * s), "GNG_SEZ", -1.0, "isomorphic"),
        ("LH_innate", int(65 * s), "LH", +1.0, "isomorphic"),
        ("CX_ring", int(70 * s), "CX", +1.0, "isomorphic"),
        ("CX_inh", int(24 * s), "CX", -1.0, "isomorphic"),
        ("LAL_premotor", int(50 * s), "CENTRAL_OTHER", +1.0, "isomorphic"),
        ("DNa_turn", max(8, int(14 * s)), "DN_MOTOR", +1.0, "isomorphic"),
        ("P9_walk", max(8, int(12 * s)), "DN_MOTOR", +1.0, "isomorphic"),
        ("MDN_GF_escape", max(8, int(12 * s)), "DN_MOTOR", +1.0, "isomorphic"),
        ("aDN1_groom", max(6, int(10 * s)), "DN_MOTOR", +1.0, "isomorphic"),
        ("MN9_feed", max(6, int(10 * s)), "VNC_MOTOR", +1.0, "isomorphic"),
        ("MN_walk", max(12, int(24 * s)), "VNC_MOTOR", +1.0, "isomorphic"),
        ("MN_turn", max(12, int(24 * s)), "VNC_MOTOR", +1.0, "isomorphic"),
        ("MN_halt", max(10, int(18 * s)), "VNC_MOTOR", +1.0, "isomorphic"),
        ("MN_wing", max(10, int(18 * s)), "VNC_MOTOR", +1.0, "dimorphic"),
    ]

    rows = []
    base_id = 500_000_000 if male else 720575940600000000
    groups: Dict[str, np.ndarray] = {}
    cursor = 0
    for ctype, count, region, sign, dim in specs:
        count = max(2, count)
        idxs = np.arange(cursor, cursor + count, dtype=np.int32)
        groups[ctype] = idxs
        for k, idx in enumerate(idxs):
            side = "left" if k % 2 == 0 else "right"
            nt = "gaba" if sign < 0 else "acetylcholine"
            rows.append({
                "idx": int(idx),
                "root_id": int(base_id + idx),
                "cell_type": ctype,
                "cell_class": region,
                "region": region,
                "top_nt": nt,
                "nt_sign": float(sign),
                "side": side,
                "dimorphism": dim,
            })
        cursor += count

    nodes = pd.DataFrame(rows)
    N = len(nodes)

    # Направленные проекции (источник, приёмник, плотность, диапазон синапсов)
    motifs = [
        ("sugar_GRN", "GNG_relay", 0.32, (6, 18)),
        ("GNG_relay", "MN9_feed", 0.35, (6, 16)),
        ("GNG_relay", "P9_walk", 0.16, (3, 9)),
        ("bitter_GRN", "GNG_inh", 0.35, (6, 16)),
        ("GNG_inh", "GNG_relay", 0.35, (5, 14)),
        ("GNG_inh", "MN9_feed", 0.30, (5, 14)),
        ("bitter_GRN", "LH_innate", 0.22, (4, 11)),
        ("JO", "AMMC_B1", 0.32, (6, 15)),
        ("JO", "AMMC_inh", 0.28, (5, 12)),
        ("AMMC_B1", "WED_VLP", 0.30, (5, 14)),
        ("AMMC_inh", "AMMC_B1", 0.30, (4, 11)),
        ("AMMC_inh", "WED_VLP", 0.26, (4, 10)),
        ("WED_VLP", "vPN1", 0.32, (5, 14)),
        ("WED_VLP", "aDN1_groom", 0.28, (5, 14)),
        ("JO", "aDN1_groom", 0.14, (3, 8)),
        ("vPN1", "pC1", 0.38, (6, 16)),
        ("pC1", "P1", 0.42, (6, 16)),
        ("P1", "MN_wing", 0.36, (6, 15)),
        ("pC1", "MN_wing", 0.24, (4, 11)),
        ("P1", "P9_walk", 0.25, (4, 10)),
        ("LC_VPN", "LPLC_loom", 0.42, (6, 16)),
        ("LC_VPN", "WED_VLP", 0.30, (5, 13)),
        ("LPLC_loom", "WED_VLP", 0.30, (5, 13)),
        ("LPLC_loom", "MDN_GF_escape", 0.38, (6, 16)),
        ("WED_VLP", "MDN_GF_escape", 0.24, (5, 13)),
        ("LC_VPN", "KCg", 0.06, (2, 6)),
        ("LC_VPN", "PPL1", 0.14, (2, 7)),
        ("LC_VPN", "pC1", 0.18, (3, 9)),
        ("PN", "KCg", 0.08, (3, 9)),
        ("PN", "KCab", 0.08, (3, 9)),
        ("PN", "LH_innate", 0.22, (4, 11)),
        ("Or67d_PN", "KCg", 0.12, (3, 9)),
        ("Or67d_PN", "LH_innate", 0.28, (5, 13)),
        ("Or67d_PN", "pC1", 0.20, (3, 9)),
        ("KCg", "APL", 0.45, (4, 10)),
        ("KCab", "APL", 0.45, (4, 10)),
        ("APL", "KCg", 0.55, (3, 8)),
        ("APL", "KCab", 0.55, (3, 8)),
        ("KCg", "MBON_app", 0.34, (3, 10)),
        ("KCg", "MBON_avo", 0.34, (3, 10)),
        ("KCab", "MBON_app", 0.32, (3, 10)),
        ("KCab", "MBON_avo", 0.32, (3, 10)),
        ("PPL1", "MBON_app", 0.35, (4, 10)),
        ("PAM", "MBON_avo", 0.35, (4, 10)),
        ("aSP13_PAM", "MBON_app", 0.38, (4, 11)),
        ("MBON_app", "LAL_premotor", 0.36, (5, 14)),
        ("MBON_app", "P9_walk", 0.42, (6, 16)),
        ("MBON_app", "pC1", 0.32, (5, 13)),
        ("MBON_avo", "LAL_premotor", 0.34, (5, 14)),
        ("MBON_avo", "DNa_turn", 0.46, (7, 18)),
        ("MBON_avo", "MDN_GF_escape", 0.42, (7, 18)),
        ("LH_innate", "LAL_premotor", 0.26, (4, 11)),
        ("LH_innate", "DNa_turn", 0.24, (4, 11)),
        ("CX_ring", "CX_ring", 0.16, (2, 7)),
        ("CX_ring", "CX_inh", 0.30, (4, 10)),
        ("CX_inh", "CX_ring", 0.32, (4, 10)),
        ("CX_ring", "LAL_premotor", 0.28, (4, 11)),
        ("LAL_premotor", "DNa_turn", 0.32, (5, 13)),
        ("LAL_premotor", "P9_walk", 0.30, (5, 13)),
        ("P9_walk", "MN_walk", 0.42, (6, 16)),
        ("DNa_turn", "MN_turn", 0.44, (6, 16)),
        ("MDN_GF_escape", "MN_halt", 0.42, (6, 16)),
        ("MDN_GF_escape", "MN_turn", 0.26, (4, 11)),
    ]

    pre_l, post_l, cnt_l = [], [], []
    for src_t, dst_t, prob, (lo, hi) in motifs:
        s_idx, d_idx = groups[src_t], groups[dst_t]
        mask = rng.random((s_idx.size, d_idx.size)) < prob
        ii, jj = np.where(mask)
        if ii.size == 0:
            continue
        p_arr = s_idx[ii]
        q_arr = d_idx[jj]
        keep = p_arr != q_arr
        p_arr, q_arr = p_arr[keep], q_arr[keep]
        if p_arr.size:
            pre_l.append(p_arr)
            post_l.append(q_arr)
            cnt_l.append(rng.integers(lo, hi + 1, size=p_arr.size))

    # Разреженный фоновый каркас между центральными областями
    n_bg = int(N * 5)
    bg_pre = rng.integers(0, N, size=n_bg, dtype=np.int32)
    bg_post = rng.integers(0, N, size=n_bg, dtype=np.int32)
    keep = bg_pre != bg_post
    pre_all = np.concatenate(pre_l + [bg_pre[keep]])
    post_all = np.concatenate(post_l + [bg_post[keep]])
    cnt_all = np.concatenate(cnt_l + [rng.integers(1, 4, size=int(keep.sum()))])

    edf = pd.DataFrame({"pre_idx": pre_all, "post_idx": post_all, "syn_count": cnt_all.astype(float)})
    edf = edf.groupby(["pre_idx", "post_idx"], as_index=False)["syn_count"].sum()
    signs = nodes["nt_sign"].to_numpy()
    rids = nodes["root_id"].to_numpy()
    edf["signed_weight"] = edf["syn_count"].to_numpy() * signs[edf["pre_idx"].to_numpy()]
    edf["pre_id"] = rids[edf["pre_idx"].to_numpy()]
    edf["post_id"] = rids[edf["post_idx"].to_numpy()]
    label = "синтетика MaleCNS" if male else "синтетика FlyWire"
    return nodes, edf, label


def _subset_graph(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    max_neurons: int,
    priority_mask: Optional[np.ndarray] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Обрезает крупный коннектом до связного ядра max_neurons, сохраняя приоритетные клетки."""
    if max_neurons <= 0 or len(nodes) <= max_neurons:
        return nodes, edges
    deg = np.bincount(edges["pre_idx"].to_numpy(), minlength=len(nodes)) + np.bincount(
        edges["post_idx"].to_numpy(), minlength=len(nodes)
    )
    chosen: List[int] = []
    if priority_mask is not None and priority_mask.any():
        prio = np.flatnonzero(priority_mask)
        if prio.size > max_neurons // 2:
            order_p = prio[np.argsort(-deg[prio])[: max_neurons // 2]]
            chosen.extend(order_p.tolist())
        else:
            chosen.extend(prio.tolist())
    rem = max_neurons - len(chosen)
    if rem > 0:
        taken = np.zeros(len(nodes), dtype=bool)
        taken[chosen] = True
        rest = np.flatnonzero(~taken)
        top_rest = rest[np.argsort(-deg[rest])[:rem]]
        chosen.extend(top_rest.tolist())
    keep_idx = np.array(sorted(set(chosen)), dtype=np.int32)
    remap = np.full(len(nodes), -1, dtype=np.int32)
    remap[keep_idx] = np.arange(keep_idx.size, dtype=np.int32)
    sub_e = edges[(remap[edges["pre_idx"].to_numpy()] >= 0) & (remap[edges["post_idx"].to_numpy()] >= 0)].copy()
    sub_e["pre_idx"] = remap[sub_e["pre_idx"].to_numpy()]
    sub_e["post_idx"] = remap[sub_e["post_idx"].to_numpy()]
    sub_n = nodes.iloc[keep_idx].copy().reset_index(drop=True)
    sub_n["idx"] = np.arange(len(sub_n), dtype=np.int32)
    return sub_n, sub_e.reset_index(drop=True)


def load_flywire(
    data_dir: Optional[Path] = None,
    max_neurons: int = 0,
    seed: int = 0,
    synth: bool = False,
    synth_scale: float = 1.0,
) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    """Загружает FlyWire v783 из FLY_DATA (Completeness + Connectivity + опционально аннотации Schlegel).

    Корректно разбирает оба формата Connectivity:
      1) официальный eonsystemspbc/fly-brain: Presynaptic_Index, Postsynaptic_Index, Connectivity, Excitatory x Connectivity;
      2) таблицы вида pre_root_id / post_root_id / syn_count.
    Если данных на диске ещё нет или передан synth=True, возвращает модульную синтетику той же схемы.
    """
    if synth:
        return build_synthetic_connectome(n_scale=synth_scale, seed=seed, male=False)

    d = Path(data_dir) if data_dir else DATA
    comp_p = d / "2025_Completeness_783.csv"
    conn_p = d / "2025_Connectivity_783.parquet"
    if not (comp_p.exists() and conn_p.exists() and comp_p.stat().st_size > 1000 and conn_p.stat().st_size > 1000):
        print("Реальные таблицы FlyWire v783 не найдены в FLY_DATA, использую модульную синтетику.")
        return build_synthetic_connectome(n_scale=synth_scale, seed=seed, male=False)

    comp = pd.read_csv(comp_p, index_col=0)
    root_ids = comp.index.to_numpy(dtype=np.int64)
    N = root_ids.size
    nodes = pd.DataFrame({
        "idx": np.arange(N, dtype=np.int32),
        "root_id": root_ids,
        "cell_type": "unknown",
        "cell_class": "",
        "region": "CENTRAL_OTHER",
        "top_nt": "acetylcholine",
        "nt_sign": 1.0,
        "side": "unknown",
        "dimorphism": "isomorphic",
    })
    id_to_idx = {int(r): i for i, r in enumerate(root_ids)}

    # Известные функциональные наборы из Shiu et al. 2024
    for label, id_list in SHIU_V783_SETS.items():
        present = [id_to_idx[x] for x in id_list if x in id_to_idx]
        if present:
            nodes.loc[present, "cell_type"] = label
            nodes.loc[present, "region"] = infer_region(label)

    # sez_neurons.pickle, если скачан
    sez_p = d / "sez_neurons.pickle"
    if sez_p.exists() and sez_p.stat().st_size > 100:
        try:
            sez = pickle.loads(sez_p.read_bytes())
            if isinstance(sez, dict):
                for cname, id_list in sez.items():
                    present = [id_to_idx[int(x)] for x in id_list if int(x) in id_to_idx]
                    if present:
                        nodes.loc[present, "cell_type"] = str(cname)
                        nodes.loc[present, "region"] = "GNG_SEZ"
        except Exception:
            pass

    # Аннотации Schlegel et al. 2024 (Supplemental_file1_neuron_annotations.tsv), если скачаны
    for ann_name in ("Supplemental_file1_neuron_annotations.tsv", "flywire_annotations.tsv", "flywire_annotations.parquet"):
        ann_p = d / ann_name
        if ann_p.exists() and ann_p.stat().st_size > 1000:
            ann = (
                pd.read_parquet(ann_p)
                if ann_p.suffix == ".parquet"
                else pd.read_csv(ann_p, sep="\t" if ann_p.suffix == ".tsv" else ",", low_memory=False)
            )
            low = {c.lower(): c for c in ann.columns}
            rid_c = low.get("root_id") or low.get("flywire_id")
            if rid_c:
                ann = ann.drop_duplicates(subset=[rid_c]).set_index(rid_c)
                common = nodes["root_id"].isin(ann.index)
                r_common = nodes.loc[common, "root_id"]
                for src_c, dst_c in (
                    ("cell_type", "cell_type"),
                    ("cell_class", "cell_class"),
                    ("top_nt", "top_nt"),
                    ("side", "side"),
                    ("dimorphism", "dimorphism"),
                ):
                    actual = low.get(src_c)
                    if actual:
                        vals = ann.loc[r_common, actual].fillna("").astype(str).to_numpy()
                        mask_nonempty = vals != ""
                        idx_rows = nodes.index[common].to_numpy()[mask_nonempty]
                        nodes.loc[idx_rows, dst_c] = vals[mask_nonempty]
                sc_col = low.get("super_class")
                sc_vals = ann.loc[r_common, sc_col].fillna("").astype(str).to_numpy() if sc_col else [""] * int(common.sum())
                ct_vals = nodes.loc[common, "cell_type"].to_numpy()
                cc_vals = nodes.loc[common, "cell_class"].to_numpy()
                nodes.loc[common, "region"] = [
                    infer_region(ct, cc, sc) for ct, cc, sc in zip(ct_vals, cc_vals, sc_vals)
                ]
                nodes["nt_sign"] = nt_to_sign(nodes["top_nt"])
            break

    conn = pd.read_parquet(conn_p)
    cols = {c.lower(): c for c in conn.columns}
    if "presynaptic_index" in cols and "postsynaptic_index" in cols:
        pre_idx = conn[cols["presynaptic_index"]].to_numpy(dtype=np.int32)
        post_idx = conn[cols["postsynaptic_index"]].to_numpy(dtype=np.int32)
        if "excitatory x connectivity" in cols:
            signed_w = conn[cols["excitatory x connectivity"]].to_numpy(dtype=float)
            syn_c = np.abs(signed_w)
        else:
            w_col = cols.get("connectivity") or cols.get("weight")
            syn_c = conn[w_col].to_numpy(dtype=float) if w_col else np.ones(len(conn))
            signed_w = syn_c * nodes["nt_sign"].to_numpy()[pre_idx]
        edges = pd.DataFrame({
            "pre_idx": pre_idx,
            "post_idx": post_idx,
            "syn_count": syn_c,
            "signed_weight": signed_w,
            "pre_id": root_ids[pre_idx],
            "post_id": root_ids[post_idx],
        })
        # Восстанавливаем знак пресинаптического нейрона из знака его синапсов
        neg_pre = np.bincount(pre_idx[signed_w < 0], minlength=N)
        pos_pre = np.bincount(pre_idx[signed_w > 0], minlength=N)
        nodes["nt_sign"] = np.where(neg_pre > pos_pre, -1.0, 1.0)
    else:
        pre_c = cols.get("pre") or cols.get("pre_root_id") or cols.get("pre_pt_root_id")
        post_c = cols.get("post") or cols.get("post_root_id") or cols.get("post_pt_root_id")
        w_c = cols.get("weight") or cols.get("syn_count") or cols.get("count")
        pre_id = conn[pre_c].to_numpy(dtype=np.int64)
        post_id = conn[post_c].to_numpy(dtype=np.int64)
        p_idx = np.array([id_to_idx.get(int(x), -1) for x in pre_id], dtype=np.int32)
        q_idx = np.array([id_to_idx.get(int(x), -1) for x in post_id], dtype=np.int32)
        ok = (p_idx >= 0) & (q_idx >= 0)
        syn_c = conn[w_c].to_numpy(dtype=float)[ok] if w_c else np.ones(int(ok.sum()))
        signs = nodes["nt_sign"].to_numpy()
        edges = pd.DataFrame({
            "pre_idx": p_idx[ok],
            "post_idx": q_idx[ok],
            "syn_count": syn_c,
            "signed_weight": syn_c * signs[p_idx[ok]],
            "pre_id": pre_id[ok],
            "post_id": post_id[ok],
        })

    # Если аннотации типов ещё не скачаны, размечаем области топологически по связям с известными входами
    unknown_reg = nodes["region"] == "CENTRAL_OTHER"
    if unknown_reg.mean() > 0.85:
        out_deg = np.bincount(edges["pre_idx"].to_numpy(), minlength=N)
        in_deg = np.bincount(edges["post_idx"].to_numpy(), minlength=N)
        buckets = ["GNG_SEZ", "AVLP_WED", "MB", "CX", "LH", "AL"]
        # Детерминированное разбиение узлов без аннотаций по профилю степеней и остатку root_id
        unk_idx = np.flatnonzero(unknown_reg)
        codes = (nodes.loc[unk_idx, "root_id"].to_numpy() // 17 + (out_deg[unk_idx] > in_deg[unk_idx])) % len(buckets)
        nodes.loc[unk_idx, "region"] = [buckets[int(c)] for c in codes]

    prio = nodes["cell_type"] != "unknown"
    nodes, edges = _subset_graph(nodes, edges, max_neurons=max_neurons, priority_mask=prio.to_numpy())
    return nodes, edges, "FlyWire v783"


def load_malecns(
    data_dir: Optional[Path] = None,
    max_neurons: int = 0,
    seed: int = 0,
    synth: bool = False,
    synth_scale: float = 1.0,
) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    """Загружает коннектом самца MaleCNS v1.0 (parquet от шаблона 08 или feather из бакета Janelia)."""
    if synth:
        return build_synthetic_connectome(n_scale=synth_scale, seed=seed, male=True)

    d = Path(data_dir) if data_dir else DATA
    edge_cands = [d / "malecns_edgelist.parquet"] + sorted(d.glob("connectome-weights-male-cns*.feather"))
    edge_p = next((p for p in edge_cands if p.exists() and p.stat().st_size > 1000), None)
    if edge_p is None:
        print("Таблицы связей MaleCNS не найдены в FLY_DATA, использую синтетику MaleCNS.")
        return build_synthetic_connectome(n_scale=synth_scale, seed=seed, male=True)

    raw_e = pd.read_feather(edge_p) if edge_p.suffix == ".feather" else pd.read_parquet(edge_p)
    ecols = {c.lower().replace("_", ""): c for c in raw_e.columns}
    pre_c = ecols.get("pre") or ecols.get("bodypre") or ecols.get("bodyidpre") or ecols.get("prerootid")
    post_c = ecols.get("post") or ecols.get("bodypost") or ecols.get("bodyidpost") or ecols.get("postrootid")
    w_c = ecols.get("weight") or ecols.get("syncount") or ecols.get("count") or ecols.get("nsyn")
    if not (pre_c and post_c):
        return build_synthetic_connectome(n_scale=synth_scale, seed=seed, male=True)

    pre_id = raw_e[pre_c].to_numpy(dtype=np.int64)
    post_id = raw_e[post_c].to_numpy(dtype=np.int64)
    syn_c = raw_e[w_c].to_numpy(dtype=float) if w_c else np.ones(len(raw_e))
    keep = pre_id != post_id
    pre_id, post_id, syn_c = pre_id[keep], post_id[keep], syn_c[keep]

    root_ids = np.union1d(pre_id, post_id).astype(np.int64)
    id_to_idx = {int(r): i for i, r in enumerate(root_ids)}
    nodes = pd.DataFrame({
        "idx": np.arange(root_ids.size, dtype=np.int32),
        "root_id": root_ids,
        "cell_type": "unknown",
        "cell_class": "",
        "region": "CENTRAL_OTHER",
        "top_nt": "acetylcholine",
        "nt_sign": 1.0,
        "side": "unknown",
        "dimorphism": "isomorphic",
    })

    ann_cands = [d / "malecns_neurons.parquet"] + sorted(d.glob("body-annotations-male-cns*.feather"))
    ann_p = next((p for p in ann_cands if p.exists() and p.stat().st_size > 500), None)
    if ann_p is not None:
        ann = pd.read_feather(ann_p) if ann_p.suffix == ".feather" else pd.read_parquet(ann_p)
        ac = {c.lower().replace("_", ""): c for c in ann.columns}
        rid_c = ac.get("bodyid") or ac.get("rootid") or ac.get("id") or ac.get("body")
        if rid_c:
            ann = ann.drop_duplicates(subset=[rid_c]).set_index(rid_c)
            common = nodes["root_id"].isin(ann.index)
            r_common = nodes.loc[common, "root_id"]
            for key, dst_c in (("type", "cell_type"), ("celltype", "cell_type"), ("class", "cell_class"),
                               ("superclass", "cell_class"), ("side", "side"), ("dimorphism", "dimorphism")):
                if key in ac:
                    vals = ann.loc[r_common, ac[key]].fillna("").astype(str).to_numpy()
                    nonempty = vals != ""
                    nodes.loc[nodes.index[common].to_numpy()[nonempty], dst_c] = vals[nonempty]
            nodes.loc[common, "region"] = [
                infer_region(ct, cc) for ct, cc in zip(nodes.loc[common, "cell_type"], nodes.loc[common, "cell_class"])
            ]

    nt_cands = sorted(d.glob("body-neurotransmitters-male-cns*.feather"))
    if nt_cands:
        nt_df = pd.read_feather(nt_cands[0])
        nc = {c.lower().replace("_", ""): c for c in nt_df.columns}
        rid_c = nc.get("bodyid") or nc.get("rootid") or nc.get("body")
        nt_c = nc.get("topnt") or nc.get("nttype") or nc.get("neurotransmitter") or nc.get("nt")
        if rid_c and nt_c:
            nt_df = nt_df.drop_duplicates(subset=[rid_c]).set_index(rid_c)
            common = nodes["root_id"].isin(nt_df.index)
            nodes.loc[common, "top_nt"] = nt_df.loc[nodes.loc[common, "root_id"], nt_c].astype(str).to_numpy()
            nodes["nt_sign"] = nt_to_sign(nodes["top_nt"])

    p_idx = np.array([id_to_idx[int(x)] for x in pre_id], dtype=np.int32)
    q_idx = np.array([id_to_idx[int(x)] for x in post_id], dtype=np.int32)
    edges = pd.DataFrame({
        "pre_idx": p_idx,
        "post_idx": q_idx,
        "syn_count": syn_c,
        "signed_weight": syn_c * nodes["nt_sign"].to_numpy()[p_idx],
        "pre_id": pre_id,
        "post_id": post_id,
    })
    prio = nodes["cell_type"] != "unknown"
    nodes, edges = _subset_graph(nodes, edges, max_neurons=max_neurons, priority_mask=prio.to_numpy())
    return nodes, edges, "MaleCNS v1.0"


def build_weight_matrix(
    n_nodes: int,
    edges: pd.DataFrame,
    w_syn: float = 0.275,
    weight_scale: float = 1.0,
    clip_mv: float = 10.0,
) -> sparse.csr_matrix:
    """Строит разреженную матрицу W_post_pre (размер N x N), где y = W_post_pre @ spikes."""
    pre = edges["pre_idx"].to_numpy(dtype=np.int32)
    post = edges["post_idx"].to_numpy(dtype=np.int32)
    w = np.clip(edges["signed_weight"].to_numpy(dtype=np.float32) * float(w_syn * weight_scale), -clip_mv, clip_mv)
    return sparse.csr_matrix((w, (post, pre)), shape=(n_nodes, n_nodes), dtype=np.float32)


def degree_preserving_shuffle(edges: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Перемешивает постсинаптических партнёров отдельно внутри возб. и торм. связей."""
    out = edges.copy()
    post = out["post_idx"].to_numpy().copy()
    post_id = out["post_id"].to_numpy().copy()
    exc = out["signed_weight"].to_numpy() >= 0
    for mask in (exc, ~exc):
        idx = np.flatnonzero(mask)
        if idx.size > 1:
            perm = rng.permutation(idx.size)
            post[idx] = post[idx[perm]]
            post_id[idx] = post_id[idx[perm]]
    out["post_idx"] = post
    out["post_id"] = post_id
    return out


def run_lif_trials(
    W_post_pre: sparse.csr_matrix,
    stim_rates_hz: Optional[Dict[int, float]] = None,
    silence_idx: Optional[Iterable[int]] = None,
    t_sec: float = 0.4,
    n_trials: int = 3,
    dt_ms: float = 0.2,
    bg_rate_hz: float = 28.0,
    w_bg_mv: float = 2.75,
    seed: int = 0,
    record_bins: int = 40,
    record_spikes_trial0: bool = False,
    v_th_offset: Optional[np.ndarray] = None,
    params: Optional[dict] = None,
) -> dict:
    """Пошаговый расчёт LIF-сети Shiu et al. 2024 на разреженной матрице CSR.

    Возвращает средние частоты (Гц) по нейронам, разброс по попыткам, PSTH по времени и (при запросе)
    список спайков первой попытки.
    """
    p = {**SHIU_DEFAULTS, **(params or {})}
    N = W_post_pre.shape[0]
    steps = max(10, int(round(t_sec * 1000.0 / dt_ms)))
    dly_steps = max(1, int(round(p["t_dly"] / dt_ms)))
    rfc_steps = max(1, int(round(p["t_rfc"] / dt_ms)))
    decay_v = math.exp(-dt_ms / p["t_mbr"])
    decay_g = math.exp(-dt_ms / p["tau_g"])
    alpha_v = 1.0 - decay_v

    v_0 = float(p["v_0"])
    v_rst = float(p["v_rst"])
    v_th = np.full(N, float(p["v_th"]), dtype=np.float32)
    if v_th_offset is not None:
        v_th = v_th + v_th_offset.astype(np.float32)

    sil_mask = np.ones(N, dtype=np.float32)
    if silence_idx is not None:
        sil_arr = np.array(list(silence_idx), dtype=np.int32)
        sil_arr = sil_arr[(sil_arr >= 0) & (sil_arr < N)]
        sil_mask[sil_arr] = 0.0

    stim_idx = np.array([], dtype=np.int32)
    stim_prob = np.array([], dtype=np.float32)
    w_poi = float(p["w_syn"] * p["f_poi"] * 0.14)
    if stim_rates_hz:
        pairs = [(int(i), float(r)) for i, r in stim_rates_hz.items() if 0 <= int(i) < N and r > 0]
        if pairs:
            stim_idx = np.array([k for k, _ in pairs], dtype=np.int32)
            stim_prob = np.array([min(0.95, r * dt_ms / 1000.0) for _, r in pairs], dtype=np.float32)

    p_bg = min(0.5, float(bg_rate_hz) * dt_ms / 1000.0)
    bin_edges = np.linspace(0, steps, record_bins + 1, dtype=int)

    rng = np.random.default_rng(seed)
    v = np.full((N, n_trials), v_0, dtype=np.float32)
    g = np.zeros((N, n_trials), dtype=np.float32)
    refrac = np.zeros((N, n_trials), dtype=np.int16)
    ring = np.zeros((dly_steps, N, n_trials), dtype=np.float32)
    trial_counts = np.zeros((N, n_trials), dtype=np.int32)
    psth = np.zeros((record_bins, N), dtype=np.float32)
    spikes_t0: List[Tuple[float, int]] = []
    v_th_col = v_th[:, None]
    sil_col = sil_mask[:, None]
    b_cur = 0

    for step in range(steps):
        while b_cur + 1 < record_bins and step >= bin_edges[b_cur + 1]:
            b_cur += 1

        delayed_spk = ring[step % dly_steps]
        if delayed_spk.any():
            g += W_post_pre.dot(delayed_spk)
            ring[step % dly_steps] = 0.0

        if p_bg > 0:
            bg_hits = rng.random((N, n_trials), dtype=np.float32) < p_bg
            v[bg_hits] += w_bg_mv

        if stim_idx.size:
            s_hits = rng.random((stim_idx.size, n_trials), dtype=np.float32) < stim_prob[:, None]
            if s_hits.any():
                v[stim_idx] += s_hits.astype(np.float32) * w_poi

        active = refrac <= 0
        v = np.where(active, v_0 + (v - v_0) * decay_v + g * alpha_v, v)
        g *= decay_g
        refrac = np.where(active, 0, refrac - 1)

        fired = active & (v > v_th_col) & (sil_col > 0.5)
        if fired.any():
            v = np.where(fired, v_rst, v)
            g = np.where(fired, 0.0, g)
            refrac = np.where(fired, rfc_steps, refrac)
            spk_mat = fired.astype(np.float32)
            ring[(step + dly_steps) % dly_steps] = spk_mat
            cnt_step = fired.sum(axis=1)
            trial_counts += fired.astype(np.int32)
            psth[b_cur] += cnt_step
            if record_spikes_trial0 and fired[:, 0].any():
                t_now = step * dt_ms / 1000.0
                spikes_t0.extend((t_now, int(i)) for i in np.flatnonzero(fired[:, 0]))

    rates = trial_counts.T.astype(np.float32) / max(t_sec, 1e-6)
    bin_dt = max(t_sec / max(record_bins, 1), 1e-6)
    psth_hz = psth / (n_trials * bin_dt)
    return {
        "rates_mean": rates.mean(axis=0),
        "rates_std": rates.std(axis=0),
        "trial_rates": rates,
        "psth_hz": psth_hz,
        "bin_centers_s": (np.arange(record_bins) + 0.5) * (t_sec / record_bins),
        "spikes_trial0": spikes_t0,
    }
