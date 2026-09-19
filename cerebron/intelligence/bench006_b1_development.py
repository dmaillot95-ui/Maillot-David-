import hashlib
import json
import random
from dataclasses import dataclass

STATE_BITS = 6
ACTION_BITS = 3
DEV_SEEDS = [6101, 6102, 6103, 6104, 6105, 6106]
PRIVATE_FIELDS = {"expected_answers", "latent_parameters", "private_family_label", "holdout_seed"}


@dataclass
class Counter:
    reads: int = 0
    xor_ops: int = 0
    and_ops: int = 0
    pivots: int = 0
    predictions: int = 0

    def total(self):
        return self.reads + self.xor_ops + self.and_ops + self.pivots + self.predictions


def bits(value, width):
    return [(value >> i) & 1 for i in range(width)]


def pack(values):
    return sum((v & 1) << i for i, v in enumerate(values))


def public_request(payload):
    unknown = set(payload) - {"request_id", "observations", "queries", "condition", "public_algorithm_seed"}
    if unknown:
        raise ValueError(f"unknown/private fields: {sorted(unknown)}")
    if PRIVATE_FIELDS.intersection(payload):
        raise ValueError("private field exposed")
    return payload


def features(state, action):
    return [1] + bits(state, STATE_BITS) + bits(action, ACTION_BITS)


def gf2_fit(rows, targets, counter):
    if not rows:
        return None
    matrix = [list(r) + [t] for r, t in zip(rows, targets)]
    cols = len(rows[0])
    pivot_row = 0
    pivots = []
    for col in range(cols):
        found = next((r for r in range(pivot_row, len(matrix)) if matrix[r][col]), None)
        if found is None:
            continue
        matrix[pivot_row], matrix[found] = matrix[found], matrix[pivot_row]
        counter.pivots += 1
        for r in range(len(matrix)):
            if r != pivot_row and matrix[r][col]:
                matrix[r] = [a ^ b for a, b in zip(matrix[r], matrix[pivot_row])]
                counter.xor_ops += len(matrix[r])
        pivots.append((pivot_row, col))
        pivot_row += 1
        if pivot_row == len(matrix):
            break
    for r in range(pivot_row, len(matrix)):
        if not any(matrix[r][:cols]) and matrix[r][cols]:
            return None
    solution = [0] * cols
    for r, col in reversed(pivots):
        rhs = matrix[r][cols]
        for j in range(col + 1, cols):
            rhs ^= matrix[r][j] & solution[j]
            counter.and_ops += 1
            counter.xor_ops += 1
        solution[col] = rhs
    return solution


def fit_affine(observations, counter, shuffled_seed=None):
    rows = [features(s, a) for s, a, _ in observations]
    outputs = [n for _, _, n in observations]
    if shuffled_seed is not None:
        outputs = outputs[:]
        random.Random(shuffled_seed).shuffle(outputs)
    counter.reads += len(observations)
    coeffs = []
    for bit_index in range(STATE_BITS):
        target = [(n >> bit_index) & 1 for n in outputs]
        coeff = gf2_fit(rows, target, counter)
        if coeff is None:
            coeff = [0] * len(rows[0])
        coeffs.append(coeff)
    return coeffs


def predict_affine(model, state, action, counter):
    row = features(state, action)
    out = []
    for coeff in model:
        value = 0
        for a, b in zip(coeff, row):
            value ^= a & b
            counter.and_ops += 1
            counter.xor_ops += 1
        out.append(value)
    counter.predictions += 1
    return pack(out)


def fit_baseline(observations, counter):
    per_action = {}
    global_counts = [[0, 0] for _ in range(STATE_BITS)]
    table = {}
    for state, action, nxt in observations:
        counter.reads += 1
        table[(state, action)] = nxt
        counts = per_action.setdefault(action, [[0, 0] for _ in range(STATE_BITS)])
        for i, value in enumerate(bits(nxt, STATE_BITS)):
            counts[i][value] += 1
            global_counts[i][value] += 1
    return table, per_action, global_counts


def predict_baseline(model, state, action, counter):
    table, per_action, global_counts = model
    counter.predictions += 1
    if (state, action) in table:
        return table[(state, action)]
    counts = per_action.get(action, global_counts)
    return pack([int(c[1] >= c[0]) for c in counts])


def make_system(seed, family):
    rng = random.Random(seed)
    width = 1 + STATE_BITS + ACTION_BITS
    coeffs = []
    for out_bit in range(STATE_BITS):
        if family == "affine_gf2":
            row = [rng.randrange(2) for _ in range(width)]
        else:
            row = [0] * width
            row[0] = rng.randrange(2)
            row[1 + out_bit] = 1
            row[1 + ((out_bit - 1) % STATE_BITS)] = rng.randrange(2)
            row[1 + ((out_bit + 1) % STATE_BITS)] = rng.randrange(2)
            row[1 + STATE_BITS + (out_bit % ACTION_BITS)] = 1
        coeffs.append(row)
    return coeffs


def transition(coeffs, state, action):
    row = features(state, action)
    return pack([sum(a & b for a, b in zip(c, row)) & 1 for c in coeffs])


def dataset(seed, family):
    coeffs = make_system(seed * 31 + 7, family)
    pairs = [(s, a) for s in range(1 << STATE_BITS) for a in range(1 << ACTION_BITS)]
    random.Random(seed * 101 + 3).shuffle(pairs)
    items = [(s, a, transition(coeffs, s, a)) for s, a in pairs[:136]]
    return items[:48], items[48:72], items[72:136], coeffs


def evaluate_condition(condition, fit, validation, queries, seed):
    counter = Counter()
    training = fit + validation
    if condition == "active":
        model = fit_affine(training, counter)
        predictor = predict_affine
    elif condition == "sham":
        model = fit_affine(training, counter, shuffled_seed=seed + 800000)
        predictor = predict_affine
    elif condition == "baseline":
        model = fit_baseline(training, counter)
        predictor = predict_baseline
    elif condition == "ablation":
        model = None
        predictor = None
    else:
        raise ValueError(condition)
    predictions = []
    for state, action, _ in queries:
        if condition == "ablation":
            local = fit_baseline(training, counter)
            pred = predict_baseline(local, state, action, counter)
        else:
            pred = predictor(model, state, action, counter)
        predictions.append(pred)
    return predictions, counter


def grade(predictions, queries):
    wrong_bits = 0
    exact = 0
    for pred, (_, _, truth) in zip(predictions, queries):
        wrong_bits += (pred ^ truth).bit_count()
        exact += int(pred == truth)
    return {"bit_error": wrong_bits / (len(queries) * STATE_BITS), "exact_accuracy": exact / len(queries)}


def run_development():
    records = []
    for seed in DEV_SEEDS:
        for family in ("affine_gf2", "local_xor_ring"):
            fit, validation, query, latent = dataset(seed, family)
            public = public_request({"request_id": f"{seed}-{family}", "observations": fit + validation,
                                     "queries": [(i, s, a) for i, (s, a, _) in enumerate(query)],
                                     "condition": "paired", "public_algorithm_seed": seed})
            public_hash = hashlib.sha256(json.dumps(public, sort_keys=True).encode()).hexdigest()
            for condition in ("baseline", "active", "sham", "ablation"):
                preds, counter = evaluate_condition(condition, fit, validation, query, seed)
                record = {"seed": seed, "family": family, "condition": condition,
                          **grade(preds, query), "operations": counter.total(),
                          "public_input_sha256": public_hash,
                          "prediction_sha256": hashlib.sha256(json.dumps(preds).encode()).hexdigest()}
                records.append(record)
            del latent
    summary = {}
    for condition in ("baseline", "active", "sham", "ablation"):
        subset = [r for r in records if r["condition"] == condition]
        summary[condition] = {
            "mean_bit_error": sum(r["bit_error"] for r in subset) / len(subset),
            "mean_exact_accuracy": sum(r["exact_accuracy"] for r in subset) / len(subset),
            "mean_operations": sum(r["operations"] for r in subset) / len(subset),
        }
    return {"benchmark_id": "BENCH-006-B1-DEVELOPMENT", "promotion_allowed": False,
            "isolation_level": "cooperative_in_process_projection_only",
            "records": records, "summary": summary,
            "claim_limit": "Development sensitivity test only; not a sealed holdout or evidence of general intelligence."}


if __name__ == "__main__":
    print(json.dumps(run_development(), indent=2, sort_keys=True))
