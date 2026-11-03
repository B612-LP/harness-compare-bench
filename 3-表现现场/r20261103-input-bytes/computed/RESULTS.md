# Instrumented mechanism results

Client-side UTF-8 assembly bytes; not tokens, costs, or final server model input. No formal product scores change.

Decision branch: `repeated_direction_information_retained`; valid DSH pairs 6/6.

| Run | Phase | Arm | Valid | Δ input bytes | Tool bytes | HEAD/TAIL retained |
|---|---|---|---|---:|---:|---|
| confirm-b01-bounded | confirmation | bounded | True | 2382 | 1981 | True |
| confirm-b01-inline | confirmation | inline | True | 36563 | 35767 | True |
| confirm-b02-bounded | confirmation | bounded | True | 2382 | 1981 | True |
| confirm-b02-inline | confirmation | inline | True | 36576 | 35767 | True |
| confirm-b03-bounded | confirmation | bounded | True | 2382 | 1981 | True |
| confirm-b03-inline | confirmation | inline | True | 36576 | 35767 | True |
| confirm-b04-bounded | confirmation | bounded | True | 2382 | 1981 | True |
| confirm-b04-inline | confirmation | inline | True | 36563 | 35767 | True |
| confirm-b05-bounded | confirmation | bounded | True | 2382 | 1981 | True |
| confirm-b05-inline | confirmation | inline | True | 36563 | 35767 | True |
| confirm-b06-bounded | confirmation | bounded | True | 2382 | 1981 | True |
| confirm-b06-inline | confirmation | inline | True | 36737 | 35767 | True |
| pilot-dsh | pilot | bounded | False | unknown | unknown | unknown |
| pilot-dsh-v2 | pilot | bounded | True | 2382 | 1981 | True |

| Block | Valid | Inline minus bounded Δ bytes | First input equal |
|---|---|---:|---|
| 1 | True | 34181 | True |
| 2 | True | 34194 | True |
| 3 | True | 34194 | True |
| 4 | True | 34181 | True |
| 5 | True | 34181 | True |
| 6 | True | 34355 | True |

## Limits
- Native system/tool/schema and output budgets can differ between products. Only DSH local threshold contrast is an intervention.
- The relay buffers streaming responses and changes chunk timing/latency; no native latency or universal cost comparison.
- Reasoning setting is low, not control of actual reasoning tokens; backend context/cache/rewriting remain unseen.
- Pilots and mock calibrations are not confirmation samples. Missing/invalid attempts remain in the table.
- Real third-party witness and external public-entry reading remain pending.
