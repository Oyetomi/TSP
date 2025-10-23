import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Tuple

@dataclass
class MatchFeatures:
    match: str
    is_win: bool
    win_prob: float
    surface: str
    high_tier: bool
    opponent_rank: int | None
    ranking_gap: int | None
    abs_gap: int | None
    form_gap: float | None

HIGH_TIER_TOURNAMENTS = {
    'beijing', 'tokyo', 'shanghai', 'cincinnati', 'madrid', 'miami',
    'indian wells', 'dubai', 'doha', 'toronto', 'montreal', 'roma', 'rome'
}

SURFACE_TYPES = ['hard', 'clay', 'grass']


def parse_int(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def parse_float(value: str | None) -> float | None:
    try:
        return float(value) if value else None
    except (TypeError, ValueError):
        return None


def load_matches(validation_log: Path, all_csv: Path) -> List[MatchFeatures]:
    with validation_log.open() as f:
        results = [row for row in csv.DictReader(f) if row['Match_Finished'] == 'True']

    with all_csv.open() as f:
        info = {f"{row['player1_name']} vs {row['player2_name']}": row for row in csv.DictReader(f)}

    features: List[MatchFeatures] = []
    for res in results:
        row = info.get(res['Match'])
        if not row:
            continue

        predicted = row['predicted_winner']
        win_prob = parse_float(row.get('win_probability')) or 0.0
        surface = (row.get('surface') or '').lower()
        tournament = (row.get('tournament') or '').lower()
        high_tier = any(keyword in tournament for keyword in HIGH_TIER_TOURNAMENTS)

        if predicted == row['player1_name']:
            pred_rank = parse_int(row.get('player1_ranking'))
            opp_rank = parse_int(row.get('player2_ranking'))
            pred_form = parse_float(row.get('player1_form_score'))
            opp_form = parse_float(row.get('player2_form_score'))
        else:
            pred_rank = parse_int(row.get('player2_ranking'))
            opp_rank = parse_int(row.get('player1_ranking'))
            pred_form = parse_float(row.get('player2_form_score'))
            opp_form = parse_float(row.get('player1_form_score'))

        abs_gap = None
        ranking_gap = None
        if pred_rank is not None and opp_rank is not None:
            abs_gap = abs(pred_rank - opp_rank)
            ranking_gap = pred_rank - opp_rank

        form_gap = None
        if pred_form is not None and opp_form is not None:
            form_gap = opp_form - pred_form

        features.append(MatchFeatures(
            match=res['Match'],
            is_win=res['Prediction_Correct'] == 'True',
            win_prob=win_prob,
            surface=surface,
            high_tier=high_tier,
            opponent_rank=opp_rank,
            ranking_gap=ranking_gap,
            abs_gap=abs_gap,
            form_gap=form_gap,
        ))
    return features


FilterFunc = Callable[[MatchFeatures], bool]


def evaluate_filter(matches: List[MatchFeatures], filter_func: FilterFunc) -> Tuple[int, int, int, int]:
    losses_hidden = 0
    losses_shown = 0
    wins_hidden = 0
    wins_shown = 0

    for match in matches:
        flagged = filter_func(match)
        if match.is_win:
            if flagged:
                wins_hidden += 1
            else:
                wins_shown += 1
        else:
            if flagged:
                losses_hidden += 1
            else:
                losses_shown += 1

    return losses_hidden, losses_shown, wins_hidden, wins_shown


def build_filter(win_prob: float, abs_gap: int, form_gap: float, high_tier_only: bool, surface: str) -> FilterFunc:
    def _filter(match: MatchFeatures) -> bool:
        if high_tier_only and not match.high_tier:
            return False
        if surface and surface not in match.surface:
            return False
        if match.win_prob < win_prob:
            return False
        if abs_gap >= 0:
            if match.abs_gap is None or match.abs_gap > abs_gap:
                return False
        if form_gap >= 0:
            if match.form_gap is None or match.form_gap < form_gap:
                return False
        return True
    return _filter


def generate_filters() -> List[Tuple[Dict[str, float | int | bool | str], FilterFunc]]:
    thresholds_win_prob = [0.62, 0.65, 0.68, 0.7, 0.72]
    thresholds_gap = [10, 15, 20, 25, 30]
    thresholds_form = [-1, 5, 8, 10, 12]
    surfaces = ['', *SURFACE_TYPES]
    filters: List[Tuple[Dict[str, float | int | bool | str], FilterFunc]] = []
    for wp in thresholds_win_prob:
        for gap in thresholds_gap:
            for fg in thresholds_form:
                for high_tier_flag in (False, True):
                    for surface in surfaces:
                        params = {
                            'win_prob': wp,
                            'max_gap': gap,
                            'min_form_gap': fg,
                            'high_tier_only': high_tier_flag,
                            'surface': surface,
                        }
                        filters.append((params, build_filter(wp, gap, fg, high_tier_flag, surface)))
    return filters


def main():
    validation_log = Path('logs/validation_all_20250925_233123.csv')
    all_csv = Path('all.csv')
    matches = load_matches(validation_log, all_csv)
    filters = generate_filters()

    best = []
    for idx, (params, rule) in enumerate(filters):
        losses_hidden, losses_shown, wins_hidden, wins_shown = evaluate_filter(matches, rule)
        if losses_hidden == 0:
            continue
        precision = losses_hidden / (losses_hidden + wins_hidden) if (losses_hidden + wins_hidden) else 0
        recall = losses_hidden / (losses_hidden + losses_shown) if (losses_hidden + losses_shown) else 0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0
        best.append((f1, losses_hidden, wins_hidden, params, idx))

    best.sort(reverse=True, key=lambda x: (x[0], x[1]))
    print('Top filter candidates (f1, losses_hidden, wins_hidden, rule_index, params):')
    for f1, l_hidden, w_hidden, params, idx in best[:10]:
        print(
            f"F1={f1:.3f}, losses_hidden={l_hidden}, wins_hidden={w_hidden}, id={idx}, params={params}"
        )


if __name__ == '__main__':
    main()
