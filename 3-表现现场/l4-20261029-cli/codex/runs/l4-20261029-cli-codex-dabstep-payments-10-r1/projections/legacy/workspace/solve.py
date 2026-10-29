import csv
import json
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP


ROOT = "."
YEAR_END_DAYS = [31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365]


def month_of(day_of_year):
    for month, end in enumerate(YEAR_END_DAYS, 1):
        if day_of_year <= end:
            return month
    raise ValueError(day_of_year)


def decimal(value):
    return Decimal(str(value))


def is_credit_match(rule_credit, credit):
    return rule_credit is None or rule_credit is credit


def list_match(values, value):
    return not values or value in values


def capture_delay_match(rule_delay, merchant_delay):
    if rule_delay is None:
        return True
    if merchant_delay in {"1", "2"}:
        merchant_delay = "<3"
    elif merchant_delay == "7":
        merchant_delay = ">5"
    return rule_delay == merchant_delay


def volume_match(rule_volume, volume):
    if rule_volume is None:
        return True
    if rule_volume == "<100k":
        return volume < 100_000
    if rule_volume == "100k-1m":
        return 100_000 <= volume <= 1_000_000
    if rule_volume == "1m-5m":
        return 1_000_000 <= volume <= 5_000_000
    if rule_volume == ">5m":
        return volume > 5_000_000
    raise ValueError(rule_volume)


def fraud_match(rule_fraud, fraud_rate):
    if rule_fraud is None:
        return True
    pct = fraud_rate * 100
    if rule_fraud == "<7.2%":
        return pct < 7.2
    if rule_fraud == "7.2%-7.7%":
        return 7.2 <= pct <= 7.7
    if rule_fraud == "7.7%-8.3%":
        return 7.7 <= pct <= 8.3
    if rule_fraud == ">8.3%":
        return pct > 8.3
    raise ValueError(rule_fraud)


with open("inputs/fees.json", encoding="utf-8") as handle:
    fees = json.load(handle)
with open("inputs/merchant_data.json", encoding="utf-8") as handle:
    merchants = {item["merchant"]: item for item in json.load(handle)}
with open("inputs/merchant_category_codes.csv", encoding="utf-8-sig", newline="") as handle:
    mcc_by_description = {
        row["description"]: int(row["mcc"]) for row in csv.DictReader(handle)
    }

issuing_counts = Counter()
ip_transactions = Counter()
ip_fraud_transactions = Counter()
merchant_month = defaultdict(lambda: {"volume": Decimal("0"), "fraud": Decimal("0")})
merchant_day_transactions = defaultdict(list)
merchant_month_transactions = defaultdict(list)

with open("inputs/payments.csv", encoding="utf-8", newline="") as handle:
    for row in csv.DictReader(handle):
        day = int(row["day_of_year"])
        month = month_of(day)
        amount = decimal(row["eur_amount"])
        is_fraud = row["has_fraudulent_dispute"] == "True"
        credit = row["is_credit"] == "True"
        domestic = row["issuing_country"] == row["acquirer_country"]
        transaction = {
            "card_scheme": row["card_scheme"],
            "is_credit": credit,
            "aci": row["aci"],
            "intracountry": domestic,
            "amount": amount,
        }

        issuing_counts[row["issuing_country"]] += 1
        ip_transactions[row["ip_country"]] += 1
        if is_fraud:
            ip_fraud_transactions[row["ip_country"]] += 1

        month_key = (row["merchant"], row["year"], month)
        merchant_month[month_key]["volume"] += amount
        if is_fraud:
            merchant_month[month_key]["fraud"] += amount
        merchant_day_transactions[(row["merchant"], row["year"], day)].append(transaction)
        merchant_month_transactions[(row["merchant"], row["year"], month)].append(transaction)


def matches_merchant(rule, merchant):
    return (
        list_match(rule["account_type"], merchant["account_type"])
        and capture_delay_match(rule["capture_delay"], merchant["capture_delay"])
        and list_match(rule["merchant_category_code"], merchant["merchant_category_code"])
    )


def matches_month(rule, volume, fraud):
    return volume_match(rule["monthly_volume"], volume) and fraud_match(
        rule["monthly_fraud_level"], fraud
    )


def matches_transaction(rule, transaction, aci=None):
    effective_aci = transaction["aci"] if aci is None else aci
    return (
        rule["card_scheme"] == transaction["card_scheme"]
        and is_credit_match(rule["is_credit"], transaction["is_credit"])
        and list_match(rule["aci"], effective_aci)
        and (
            rule["intracountry"] is None
            or bool(rule["intracountry"]) == transaction["intracountry"]
        )
    )


answers = {}

# 5: Most transactions by issuing country.
answers["5"] = issuing_counts.most_common(1)[0][0]

# 49: Highest fraudulent-transaction count among the four offered countries.
options = [("A", "NL"), ("B", "BE"), ("C", "ES"), ("D", "FR")]
best_letter, best_country = max(options, key=lambda item: ip_fraud_transactions[item[1]])
answers["49"] = f"{best_letter}. {best_country}"

# 70: Martinis has months above the highest fraud band (>8.3%).
martinis = merchants["Martinis_Fine_Steakhouse"]
in_danger = False
for month in range(1, 13):
    stats = merchant_month[(martinis["merchant"], "2023", month)]
    if stats["volume"] and stats["fraud"] / stats["volume"] > Decimal("0.083"):
        in_danger = True
        break
answers["70"] = "yes" if in_danger else "no"

# 1273: Average fee for GlobalCard rules applicable to credit transactions.
credit_rules = [
    rule
    for rule in fees
    if rule["card_scheme"] == "GlobalCard"
    and is_credit_match(rule["is_credit"], True)
]
credit_average = sum(
    decimal(rule["fixed_amount"]) + decimal(rule["rate"]) * Decimal("10") / Decimal("10000")
    for rule in credit_rules
) / len(credit_rules)
answers["1273"] = str(credit_average.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))

# 1305: Average GlobalCard fee for account type H / MCC 5812.
mcc = mcc_by_description["Eating Places and Restaurants"]
hsr_rules = [
    rule
    for rule in fees
    if rule["card_scheme"] == "GlobalCard"
    and list_match(rule["account_type"], "H")
    and list_match(rule["merchant_category_code"], mcc)
]
hsr_average = sum(
    decimal(rule["fixed_amount"]) + decimal(rule["rate"]) * Decimal("10") / Decimal("10000")
    for rule in hsr_rules
) / len(hsr_rules)
answers["1305"] = str(hsr_average.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))

# 1464: Rules that accept account type R and ACI B.
applicable_1464 = [
    rule["ID"]
    for rule in fees
    if list_match(rule["account_type"], "R") and list_match(rule["aci"], "B")
]
answers["1464"] = ", ".join(str(fee_id) for fee_id in applicable_1464)


def applicable_fee_ids(merchant_name, year, day=None, month=None):
    merchant = merchants[merchant_name]
    if day is not None:
        month = month_of(day)
    stats = merchant_month[(merchant_name, str(year), month)]
    volume = stats["volume"]
    fraud = stats["fraud"] / volume
    if day is not None:
        transactions = merchant_day_transactions[(merchant_name, str(year), day)]
    else:
        transactions = merchant_month_transactions[(merchant_name, str(year), month)]

    result = []
    for rule in fees:
        if not matches_merchant(rule, merchant):
            continue
        if not matches_month(rule, volume, fraud):
            continue
        if any(matches_transaction(rule, transaction) for transaction in transactions):
            result.append(rule["ID"])
    return result


# 1681 / 1753: Fee IDs observed for the merchant's relevant transactions.
answers["1681"] = ", ".join(
    str(fee_id) for fee_id in applicable_fee_ids("Belles_cookbook_store", 2023, day=10)
)
answers["1753"] = ", ".join(
    str(fee_id)
    for fee_id in applicable_fee_ids("Belles_cookbook_store", 2023, month=3)
)

# 1871: Rate change for fee ID 384 in January.
belles = merchants["Belles_cookbook_store"]
belles_jan = merchant_month[("Belles_cookbook_store", "2023", 1)]
belles_jan_fraud = belles_jan["fraud"] / belles_jan["volume"]
rule_384 = next(rule for rule in fees if rule["ID"] == 384)
matched_amount = sum(
    transaction["amount"]
    for transaction in merchant_month_transactions[("Belles_cookbook_store", "2023", 1)]
    if matches_merchant(rule_384, belles)
    and matches_month(rule_384, belles_jan["volume"], belles_jan_fraud)
    and matches_transaction(rule_384, transaction)
)
delta_1871 = Decimal(rule_384["rate"] - 1) * matched_amount / Decimal("10000")
answers["1871"] = str(delta_1871.quantize(Decimal("0.00000000000001"), rounding=ROUND_HALF_UP))

# 2697: For each scheme, choose the new ACI with the lowest per-transaction fees.
# Rebuild fraudulent transactions from the source rows, since the compact transaction
# records above intentionally contain only fee-relevant fields.
fraudulent = []
with open("inputs/payments.csv", encoding="utf-8", newline="") as handle:
    for row in csv.DictReader(handle):
        if (
            row["merchant"] == "Belles_cookbook_store"
            and month_of(int(row["day_of_year"])) == 1
            and row["has_fraudulent_dispute"] == "True"
        ):
            fraudulent.append(
                {
                    "card_scheme": row["card_scheme"],
                    "is_credit": row["is_credit"] == "True",
                    "intracountry": row["issuing_country"] == row["acquirer_country"],
                    "amount": decimal(row["eur_amount"]),
                }
            )

scheme_best = {}
for scheme in sorted({transaction["card_scheme"] for transaction in fraudulent}):
    scheme_transactions = [t for t in fraudulent if t["card_scheme"] == scheme]
    for aci in "ABCDEF":
        rules = [
            rule
            for rule in fees
            if matches_merchant(rule, belles)
            and matches_month(rule, belles_jan["volume"], belles_jan_fraud)
            and matches_transaction(rule, scheme_transactions[0], aci)
        ]
        if not rules:
            continue
        total = sum(
            min(
                decimal(rule["fixed_amount"])
                + decimal(rule["rate"]) * transaction["amount"] / Decimal("10000")
                for rule in rules
            )
            for transaction in scheme_transactions
        )
        if scheme not in scheme_best or total < scheme_best[scheme][0]:
            scheme_best[scheme] = (total, aci)

best_scheme, (best_cost, _) = min(scheme_best.items(), key=lambda item: item[1][0])
answers["2697"] = (
    f"{best_scheme}:{best_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"
)

question_order = ["5", "49", "70", "1273", "1305", "1464", "1681", "1753", "1871", "2697"]
with open("answers.jsonl", "w", encoding="utf-8") as handle:
    for task_id in question_order:
        handle.write(json.dumps({"task_id": task_id, "answer": answers[task_id]}, ensure_ascii=False) + "\n")
