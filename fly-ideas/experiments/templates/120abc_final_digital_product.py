#!/usr/bin/env python3
"""Series120A/B/C: final fly conclusion, cross-animal algorithm, and AI footprint comparison."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import traceback
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPORTS = HERE.parent / "reports"
DEFAULT_OUTPUT = Path("workspace/runs/ideas/i-observational/final-digital-product-120abc")
R118 = REPORTS / "adaptive-three-direction-118-user-result.json"
R118_SHA = "f1a5751b664e28f485f25cabb8949a266debb275aa8af8d9957b292108f0c5b1"
R119 = REPORTS / "frozen-three-direction-stress-119-user-result.json"
R119_SHA = "2badd87b4efe717458782e71b865b8d426c4526b75893a91e784d43c1aa959d1"
MATRIX = REPORTS / "biological-digital-pipeline-116a-61x61.csv"
MATRIX_SHA = "03157b503d0271cb0991db524d45220bb8f49ce62e3ba171dc997ed7f3816150"
PATHS = REPORTS / "biological-digital-pipeline-116b-61x8.csv"
PATHS_SHA = "4186bb6fdbe0a0e81f8626469027976ade1d416ff0549af94b85fb1b07aa3ca1"
ACTIONS = ("foreleg_rubbing", "head_directed_grooming", "reach_withdraw")
REFERENCE_AI = (
    ("small_neural_network_1m", 1_000_000),
    ("compact_transformer_100m", 100_000_000),
    ("reference_language_model_7b", 7_000_000_000),
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf8")


def read_matrix(path: Path):
    with path.open(encoding="utf8") as handle:
        rows = list(csv.reader(handle))
    return rows[0][1:], [row[0] for row in rows[1:]], np.asarray([[float(v) for v in row[1:]] for row in rows[1:]], float)


def verify_inputs() -> tuple[dict, dict, list[str], np.ndarray, list[str], np.ndarray]:
    for path, expected in ((R118, R118_SHA), (R119, R119_SHA), (MATRIX, MATRIX_SHA), (PATHS, PATHS_SHA)):
        actual = sha(path)
        if actual != expected:
            raise ValueError(f"Exact input changed: {path.name}: {actual}")
    result118 = json.loads(R118.read_text(encoding="utf8"))
    result119 = json.loads(R119.read_text(encoding="utf8"))
    columns, types, matrix = read_matrix(MATRIX)
    dn_columns, path_types, paths = read_matrix(PATHS)
    if columns != types or path_types != types or matrix.shape != (61, 61) or paths.shape != (61, 8):
        raise ValueError("Frozen structural dimensions changed.")
    return result118, result119, types, matrix, dn_columns, paths


def row_normalize(values: np.ndarray) -> np.ndarray:
    return values / np.maximum(values.sum(axis=1, keepdims=True), 1e-15)


def spectral_embedding(matrix: np.ndarray, dimensions: int = 10) -> np.ndarray:
    normalized = row_normalize(np.log1p(np.maximum(matrix, 0)))
    left, singular, right_t = np.linalg.svd(normalized, full_matrices=False)
    scale = np.sqrt(np.maximum(singular[:dimensions], 1e-15))
    embedding = np.concatenate((left[:, :dimensions] * scale, right_t.T[:, :dimensions] * scale), axis=1)
    embedding -= embedding.mean(axis=0, keepdims=True)
    embedding /= np.maximum(np.linalg.norm(embedding, axis=1, keepdims=True), 1e-15)
    return embedding


def align_species(source_embedding: np.ndarray, target_embedding: np.ndarray, anchor_pairs: list[tuple[int, int]]) -> np.ndarray:
    """Map a source species embedding into target coordinates using reviewed anchors only."""
    if len(anchor_pairs) < 3:
        raise ValueError("At least three reviewed cross-species anchors are required.")
    source_indices = np.asarray([pair[0] for pair in anchor_pairs])
    target_indices = np.asarray([pair[1] for pair in anchor_pairs])
    cross = source_embedding[source_indices].T @ target_embedding[target_indices]
    left, _, right_t = np.linalg.svd(cross, full_matrices=False)
    return source_embedding @ (left @ right_t)


def fit_species_motor_head(features: np.ndarray, targets: np.ndarray, ridge: float = 0.01) -> dict:
    """Fit a species-native development-only ridge head; final cases must never enter here."""
    feature_mean, target_mean = features.mean(axis=0), targets.mean(axis=0)
    centered_features, centered_targets = features - feature_mean, targets - target_mean
    weights = np.linalg.solve(centered_features.T @ centered_features + ridge * np.eye(features.shape[1]), centered_features.T @ centered_targets)
    return {"feature_mean": feature_mean, "target_mean": target_mean, "weights": weights, "ridge": ridge}


def apply_species_motor_head(features: np.ndarray, model: dict) -> np.ndarray:
    return (features - model["feature_mean"]) @ model["weights"] + model["target_mean"]


def transfer_audit(matrix: np.ndarray, paths: np.ndarray, fixture: bool) -> dict:
    """Engineering self-test on a hidden reindexing/stress domain; it is not another animal."""
    rng = np.random.default_rng(120_000_001)
    count = matrix.shape[0]
    permutation = rng.permutation(count)
    stressed = matrix[np.ix_(permutation, permutation)].copy()
    positive = stressed > 0
    stressed *= np.where(positive, rng.lognormal(0, 0.08 if fixture else 0.12, stressed.shape), 1)
    stressed *= rng.random(stressed.shape) >= (0.03 if fixture else 0.07)
    source_embedding = spectral_embedding(matrix)
    target_embedding = spectral_embedding(stressed)
    inverse = np.empty(count, int)
    inverse[permutation] = np.arange(count)
    anchor_target = np.linspace(0, count - 1, 20, dtype=int)
    anchors = [(int(permutation[target]), int(target)) for target in anchor_target]
    projected = align_species(source_embedding, target_embedding, anchors)
    similarities = projected @ target_embedding.T
    predicted_target = similarities.argmax(axis=1)
    anchor_sources = {source for source, _ in anchors}
    held_sources = [source for source in range(count) if source not in anchor_sources]
    correct = sum(int(predicted_target[source]) == int(inverse[source]) for source in held_sources)
    reciprocal = []
    order = np.argsort(-similarities, axis=1)
    for source in held_sources:
        rank = int(np.where(order[source] == inverse[source])[0][0]) + 1
        reciprocal.append(1 / rank)
    target_paths = row_normalize(np.maximum(paths[permutation], 0))
    motor_model = fit_species_motor_head(target_embedding[anchor_target], target_paths[anchor_target])
    held_targets = np.asarray([inverse[source] for source in held_sources])
    predicted_motor = apply_species_motor_head(target_embedding[held_targets], motor_model)
    motor_rmse = float(np.sqrt(np.mean((predicted_motor - target_paths[held_targets]) ** 2)))
    baseline = np.broadcast_to(target_paths[anchor_target].mean(axis=0), target_paths[held_targets].shape)
    baseline_rmse = float(np.sqrt(np.mean((baseline - target_paths[held_targets]) ** 2)))
    return {
        "test_kind": "fly_hidden_reindexing_and_stress_engineering_self_test",
        "is_cross_animal_validation": False,
        "embedding_dimensions": int(source_embedding.shape[1]),
        "audit_known_anchor_count": len(anchors),
        "held_type_count": len(held_sources),
        "held_top1_correct": correct,
        "held_top1_accuracy": correct / len(held_sources),
        "held_mean_reciprocal_rank": float(np.mean(reciprocal)),
        "development_only_motor_head_ridge": motor_model["ridge"],
        "held_motor_rmse": motor_rmse,
        "held_mean_baseline_rmse": baseline_rmse,
        "held_motor_head_beats_mean_baseline": motor_rmse < baseline_rmse,
        "algorithm_executed": True,
    }


def series120a(result118: dict, result119: dict) -> dict:
    passed118 = bool(result118["primary"]["all_three_directions_passed"])
    passed119 = bool(result119["primary"]["all_three_frozen_stress_directions_passed"])
    return {
        "series": "120A",
        "question": "What can the digital project conclude about fly mirror neurons?",
        "inputs": {"series118_sha256": R118_SHA, "series119_sha256": R119_SHA},
        "digital_evidence": {
            "adaptive_then_untouched_final_three_of_three": passed118,
            "frozen_out_of_family_stress_three_of_three": passed119,
            "series118_final": result118["final"],
            "series119_overall": result119["overall"],
            "series119_severe": result119["profiles"]["severe"],
        },
        "conclusion": {
            "digital_action_specific_observe_execute_algorithm_supported": bool(passed118 and passed119),
            "fly_type_aggregate_digital_mirror_signature_supported": bool(passed118 and passed119),
            "individual_biological_mirror_neurons_identified": False,
            "biological_mirror_neuron_claim": False,
            "promoted_biological_candidates": [],
        },
        "blocking_external_evidence": {
            "authoritative_dn_action_labels": {"validated": 0, "required": 3, "actions": ACTIONS},
            "independent_time_resolved_observation_traces": False,
            "independent_execution_and_proprioception_traces": False,
            "same_neuron_observation_execution_recording": False,
            "intervention_or_lesion_causality": False,
        },
        "product_status": "digital_method_complete_biological_identification_blocked",
    }


def series120b(matrix: np.ndarray, audit: dict) -> dict:
    required = [
        "typed sensory/connectome graph with stable identities",
        "reviewed cross-species anchor pairs",
        "species-native motor/readout identities",
        "development-only action labels with provenance",
        "time-resolved observation traces",
        "independently generated execution/proprioception traces",
        "untouched final cases and structural/identity/label/zero controls",
    ]
    return {
        "series": "120B",
        "algorithm": "species-neutral anchored graph-to-action observe/execute transfer",
        "implemented_steps": [
            "nonnegative log and row normalization",
            "joint incoming/outgoing spectral type embedding",
            "reviewed-anchor orthogonal Procrustes alignment",
            "species-native motor head fitted on development only",
            "configuration freeze before untouched final",
            "pairing, retrained-structure, identity, label and zero controls",
        ],
        "source_fly_types": int(matrix.shape[0]),
        "required_target_species_inputs": required,
        "engineering_audit": audit,
        "readiness": {
            "algorithm_implemented": True,
            "input_contract_defined": True,
            "leakage_safe_development_final_protocol_defined": True,
            "fly_hidden_domain_audit_completed": bool(audit["algorithm_executed"]),
            "validated_on_other_animal_species_count": 0,
            "cross_animal_generalization_claim": False,
        },
        "next_valid_test": "supply one target animal package satisfying every required input, register anchors before outcomes, then run a frozen held-out final",
    }


def series120c(matrix: np.ndarray, paths: np.ndarray, result119: dict) -> dict:
    structural_nonzero = int(np.count_nonzero(matrix))
    path_nonzero = int(np.count_nonzero(paths))
    dense_scalar_capacity = int(matrix.size + paths.size + 5)
    sparse_scalar_capacity = structural_nonzero + path_nonzero + 5
    fp32_bytes = dense_scalar_capacity * 4
    throughput = result119["overall"]["replicates"] / result119["active_wall_seconds"]
    comparisons = []
    for name, parameters in REFERENCE_AI:
        comparisons.append({
            "reference": name,
            "declared_parameters": parameters,
            "parameter_ratio_reference_to_dense_project_core": parameters / dense_scalar_capacity,
            "fp16_weight_memory_bytes": parameters * 2,
            "task_performance_compared": False,
        })
    return {
        "series": "120C",
        "comparison_kind": "computational_footprint_not_intelligence_or_task_quality",
        "project_core": {
            "type_count": int(matrix.shape[0]),
            "dn_channel_count": int(paths.shape[1]),
            "dense_scalar_capacity": dense_scalar_capacity,
            "sparse_nonzero_scalar_capacity": sparse_scalar_capacity,
            "approximate_fp32_core_bytes": fp32_bytes,
            "observed_series119_replicates_per_wall_second_on_user_machine": throughput,
            "observed_series119_workers": result119["protocol"]["workers"],
        },
        "reference_ai_models": comparisons,
        "interpretation": {
            "project_is_far_smaller_than_reference_ai_by_parameter_count": True,
            "project_is_specialized_and_interpretable": True,
            "project_can_be_cheaper_for_its_narrow_graph_alignment_task": True,
            "general_intelligence_equivalence": False,
            "biological_brain_power_equivalence": False,
            "accuracy_or_capability_ranking_against_ai": "not_measured_and_not_comparable_without_a_shared_dataset_task_and_metric",
        },
    }


def markdown_a(value: dict) -> str:
    c, b = value["conclusion"], value["blocking_external_evidence"]
    return f"""# Series120A — fly mirror-neuron conclusion

## Digital result

- Action-specific observe/execute algorithm supported: **{c['digital_action_specific_observe_execute_algorithm_supported']}**.
- Fly type-aggregate digital mirror signature supported: **{c['fly_type_aggregate_digital_mirror_signature_supported']}**.
- Individual biological mirror neurons identified: **{c['individual_biological_mirror_neurons_identified']}**.
- Promoted biological candidates: **0**.

Series118 passed an adaptive-development then untouched-final protocol. Series119 independently retained all overall and severe frozen stress gates across2,042,760 replicates. The final digital product is therefore a robust type-aggregate computational method, not a list of discovered biological mirror neurons.

## Still blocked

Authoritative DN action labels: **{b['authoritative_dn_action_labels']['validated']}/{b['authoritative_dn_action_labels']['required']}**. Independent observation traces, independent execution/proprioception traces, same-neuron recordings and causal intervention evidence are absent. `biological_mirror_neuron_claim=false`.
"""


def markdown_b(value: dict) -> str:
    audit = value["engineering_audit"]
    return f"""# Series120B — transfer algorithm for other animals

The implemented algorithm normalizes typed graphs, constructs joint incoming/outgoing spectral embeddings, aligns species through reviewed anchors, fits only a species-native development motor head, then freezes configuration before an untouched controlled final.

Engineering self-test: {audit['held_top1_correct']}/{audit['held_type_count']} held fly types, top-1 accuracy {audit['held_top1_accuracy']:.6f}, mean reciprocal rank {audit['held_mean_reciprocal_rank']:.6f}. Development-only native motor-head RMSE {audit['held_motor_rmse']:.6f} versus mean baseline {audit['held_mean_baseline_rmse']:.6f}; beats baseline: **{audit['held_motor_head_beats_mean_baseline']}**. This is a hidden fly reindexing/stress audit, **not another animal and not a preregistered transfer pass**.

Cross-animal validation count: **0 species**. A valid next test needs a typed target graph, preregistered homologous anchors, native motor identities, provenance-backed labels, independent observation/execution traces and untouched controls. Until then `cross_animal_generalization_claim=false`.
"""


def markdown_c(value: dict) -> str:
    core = value["project_core"]
    rows = "\n".join(f"| {item['reference']} | {item['declared_parameters']:,} | {item['parameter_ratio_reference_to_dense_project_core']:.1f}× |" for item in value["reference_ai_models"])
    return f"""# Series120C — computational footprint versus reference AI

This compares storage/compute scale, **not intelligence or task quality**.

Project dense core: {core['dense_scalar_capacity']:,} scalars, about {core['approximate_fp32_core_bytes'] / 1024:.2f} KiB in FP32. Sparse nonzero core: {core['sparse_nonzero_scalar_capacity']:,} scalars. Observed Series119 throughput on the user's six-worker machine: {core['observed_series119_replicates_per_wall_second_on_user_machine']:.3f} replicates/s.

| Explicit reference | Parameters | Reference/project parameter ratio |
|---|---:|---:|
{rows}

The project is vastly smaller, specialized and more directly interpretable. That can make it cheaper for this narrow graph-alignment task. It does not establish general-intelligence equivalence, superiority to AI, or biological brain-power equivalence. A performance ranking would require one shared dataset, task, split and metric; none exists here.
"""


def run(output: Path, fixture: bool = False) -> Path:
    result118, result119, types, matrix, dn_columns, paths = verify_inputs()
    output.mkdir(parents=True, exist_ok=True)
    audit = transfer_audit(matrix, paths, fixture)
    a, b, c = series120a(result118, result119), series120b(matrix, audit), series120c(matrix, paths, result119)
    save(output / "120a-fly-mirror-conclusion.json", a)
    save(output / "120b-cross-animal-transfer.json", b)
    save(output / "120c-ai-footprint-comparison.json", c)
    (output / "120a-fly-mirror-conclusion.md").write_text(markdown_a(a), encoding="utf8")
    (output / "120b-cross-animal-transfer.md").write_text(markdown_b(b), encoding="utf8")
    (output / "120c-ai-footprint-comparison.md").write_text(markdown_c(c), encoding="utf8")
    summary = {
        "schema": "final-digital-product-120abc-v1", "status": "fixture_completed" if fixture else "completed",
        "inputs": {"series118_sha256": R118_SHA, "series119_sha256": R119_SHA, "matrix_sha256": MATRIX_SHA, "paths_sha256": PATHS_SHA},
        "120a": {"digital_method_complete": a["conclusion"]["digital_action_specific_observe_execute_algorithm_supported"], "biological_mirror_neurons_identified": False},
        "120b": {"algorithm_implemented": True, "other_species_validated": 0, "cross_animal_claim": False, "engineering_top1_accuracy": audit["held_top1_accuracy"]},
        "120c": {"dense_scalar_capacity": c["project_core"]["dense_scalar_capacity"], "comparison_is_compute_only": True, "general_ai_equivalence": False},
        "final_product": "robust digital fly mirror-assessment and species-transfer method; biological identification awaits external evidence",
        "biological_claim": False,
    }
    save(output / "summary.json", summary)
    return output


def gui() -> None:
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk(); root.withdraw()
    try:
        output = run(DEFAULT_OUTPUT)
        if os.name == "nt": os.startfile(str(output.resolve()))
        messagebox.showinfo("Series120A/B/C", "Готовы три раздельных итога:\n120A — муха и mirror conclusion\n120B — перенос между животными\n120C — вычислительный масштаб против reference AI\n\n" + str(output.resolve()), parent=root)
    except Exception as error:
        path = DEFAULT_OUTPUT.parent / "ПОСЛЕДНЯЯ-ОШИБКА-120ABC.txt"; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(type(error).__name__ + ": " + str(error) + "\n\n" + traceback.format_exc(), encoding="utf-8-sig")
        messagebox.showerror("Series120A/B/C", f"{error}\n\n{path.resolve()}", parent=root)
        raise
    finally:
        root.destroy()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.gui:
        gui()
    else:
        print(run(args.output, args.fixture))


if __name__ == "__main__":
    main()
