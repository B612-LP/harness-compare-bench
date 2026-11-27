"""Independent arithmetic/list calibration; no filesystem inputs or candidate code."""
import json


def first_saturation_or_repeat(a, b, ages):
    """Literal predecessor membership on positions, not a packed recurrence."""
    reachable = {-age for age in ages}
    seen = {}
    for t in range(2 + (b - 1) ** 2 + b):
        last = tuple(t - i in reachable for i in range(b))
        if last in seen:
            return (seen[last], t - seen[last], all(last), any(last))
        seen[last] = t
        q = t + 1
        if any(q - step in reachable for step in range(a, b + 1)):
            reachable.add(q)
    raise RuntimeError('did not repeat inside calibration horizon')


def exact_cofinite(a, b, age):
    spread = b - a
    lo = max(a, age + 1) - age
    first_width = b - age - lo
    offset = max(0, (a - first_width - 1 + spread - 1) // spread)
    return lo + a * offset


def main():
    single_count = 0
    full_state_count = 0
    exact_by_b = []
    for b in range(1, 21):
        maximum = 0
        for a in range(1, b + 1):
            observed_worst = 0
            for age in range(b):
                tail, period, full, nonzero = first_saturation_or_repeat(a, b, (age,))
                if a < b:
                    cofinite = exact_cofinite(a, b, age)
                    expected = cofinite + b - 1 - int(cofinite == 1 and age == 0)
                    if (tail, period, full) != (expected, 1, True):
                        raise ValueError(f'bad singleton prediction {a,b,age,tail,expected}')
                    observed_worst = max(observed_worst, tail)
                    single_count += 1
                elif (tail, period, nonzero) != (0, b, True):
                    raise ValueError('wrong rotation singleton period')
            if a < b:
                formula = b + a * ((a - 1 + b - a - 1) // (b - a))
                if observed_worst != formula:
                    raise ValueError('worst singleton formula mismatch')
                maximum = max(maximum, observed_worst + 1)
            else:
                maximum = max(maximum, b)
            if b <= 8:
                for mask in range(1 << b):
                    ages = tuple(i for i in range(b) if mask & (1 << i))
                    tail, period, full, nonzero = first_saturation_or_repeat(a, b, ages)
                    if a < b and ages and (tail > observed_worst or period != 1 or not full):
                        raise ValueError('nonempty mask does not satisfy saturation bound')
                    if not ages and (tail, period, nonzero) != (0, 1, False):
                        raise ValueError('zero does not absorb')
                    if a == b and (tail or b % period):
                        raise ValueError('rotation period must divide B')
                    full_state_count += 1
        theory = 1 if b == 1 else (b - 1) ** 2 + 2
        if maximum != theory:
            raise ValueError('wrong combined orbit maximum')
        exact_by_b.append(maximum)
    print(json.dumps({
        'A_lt_B_singletons': single_count,
        'all_abstract_masks_B_le_8_including_equal_step': full_state_count,
        'distinct_states_before_repeat_B_1_to_20': exact_by_b,
        'oldest_B2_A1': first_saturation_or_repeat(1, 2, (1,)),
        'oldest_B20_A19': first_saturation_or_repeat(19, 20, (19,)),
        'identity': 'new mathematical predecessor-list calibration; no archived executions',
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
