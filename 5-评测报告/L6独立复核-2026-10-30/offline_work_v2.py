#!/usr/bin/env python3
"""Reviewer-only correction of absent CLI-specific meta field; preserve first program/logs.
Execute unchanged reviewed worker code except output root and one 8dp comparison uses
actual WB meta.weighted + score-receipt.reported. No candidate source/receipt mutation.
"""
from pathlib import Path
BASE=Path(__file__).resolve().parent
source=(BASE/'offline_work.py').read_text()
old="OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]\nS=json.loads((OUT/'snapshot-01.json').read_text());"
new="BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1];OUT=BASE/'round-02';OUT.mkdir()\nS=json.loads((BASE/'snapshot-01.json').read_text());"
assert source.count(old)==1
source=source.replace(old,new)
old2="eight==round(raw['weighted'],8)==meta['weighted_8dp']==meta['score']['reported_8dp']"
new2="eight==round(raw['weighted'],8)==round(meta['weighted'],8)==round(score['score']['reported'],8)"
assert source.count(old2)==1
source=source.replace(old2,new2)
exec(compile(source,str(BASE/'offline_work.py'),'exec'),{'__name__':'__main__','__file__':str(BASE/'offline_work.py')})
