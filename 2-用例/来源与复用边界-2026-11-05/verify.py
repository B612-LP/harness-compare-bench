#!/usr/bin/env python3
"""Read-only consistency check of a frozen source-declaration index, not legal advice.
Only seven explicitly pinned documents are read. No cited source code, solution,
checker, SQL, product answer, network, or subprocess is imported or executed.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath

BASE = '2-用例/来源与复用边界-2026-11-05/'
SOURCE_PINS = {
    '2-用例/bird-ca-schools-15/spec.md': '1dacc22e77955d987ee29b1fbeb997899e30ee0c22264a861033681beb547d26',
    '2-用例/dabstep-payments-10/spec.md': 'ef0f822d01b56089bb6fe56f1a9a6bcf7f4a1ee9796689908c8ac04a45c53852',
    '2-用例/exercism-py-6/spec.md': '1ae5102ebf4cf6fe0971f136ec536e438d977a56daa0e1bc20183ab06bead2c6',
    '2-用例/lcb-recent-hard-4/spec.md': '65c1debb503fefe9f4e813be9f414cd859fc75063fa3670c838b250772a174b9',
    '2-用例/tb-cargo-plan/spec.md': '8a94143a8333254fe5e57f7d47ea3708bd7837dd674c4189343c245f514758ea',
}
DOCUMENT_PINS = {
    BASE + 'README.md': '69939834b8dd049bc7331f0e51e0fa3d4e7ccdb776982989ea7355cbf421d7ce',
    BASE + 'sources.json': '44e8ab9fb370a1ff671d4ab455aff552d8e4d627c7208a27ba38c92c3b3d4e67',
}
# Independent frozen semantic contract, encoded as literal JSON to retain quotes.
# This constant NEVER comes from the document under test or its self-declarations.
EXPECTED_INDEX = json.loads(r'''{
  "schema": "case-source-reuse-index-v1",
  "date": "2026-11-05",
  "cases": [
    {
      "case_id": "bird-ca-schools-15",
      "source_parts": [
        {
          "name": "BIRD mini_dev / california_schools",
          "role": "benchmark_dataset",
          "url": "https://bird-bench.github.io/",
          "declared_license": "CC-BY-SA-4.0",
          "license_scope": "dataset_questions_and_gold_sql_as_declared"
        }
      ],
      "reuse_summary": "既有规格声明题面中文改写、q26 SQL及证据口径版本化修改、数据库等价重导出；数据与gold按CC BY-SA 4.0同源共享。判分器是自建exec-accuracy实现，不是官方脚本移植。",
      "evidence": [
        {
          "path": "2-用例/bird-ca-schools-15/spec.md",
          "line_start": 184,
          "line_end": 187,
          "sha256": "1dacc22e77955d987ee29b1fbeb997899e30ee0c22264a861033681beb547d26",
          "quote": "| 来源 | **BIRD**（BIg Bench for LaRge-scale Database Grounded Text-to-SQL Evaluation）· `mini_dev` split · `db_id=california_schools` |\n| 官网（榜单） | <https://bird-bench.github.io/> |\n| 论文 | <https://arxiv.org/abs/2305.03111> |\n| 数据许可 | **CC BY-SA 4.0**（署名—相同方式共享） |"
        },
        {
          "path": "2-用例/bird-ca-schools-15/spec.md",
          "line_start": 190,
          "line_end": 191,
          "sha256": "1dacc22e77955d987ee29b1fbeb997899e30ee0c22264a861033681beb547d26",
          "quote": "| 是否改写 | **题面改写**：中文重写（`question_zh` / `evidence_zh`），英文原文保留在 `questions.json` 供溯源；**SQL 仅 q26 改写**（v1.2-q26-frpm：`Free Meal Count (Ages 5-17)` → `FRPM Count (Ages 5-17)`，官方原句全文留档于 §13，其余 14 条 gold 与官方一致）；**数据未改写**（sqlite3 `backup` 等价重导出，去掉 WAL/SHM 附属文件，内容与官方 db 一致；v1.2 仅改 `questions.json` 中 q26 的 `evidence_zh` 与 `source_note` 口径说明，题干 `question_zh` 与英文原文未动） |\n| 判分器来源 | 自建实现（BIRD exec-accuracy 口径，非官方脚本移植）；`checker.py` 文件头已注明 |"
        },
        {
          "path": "2-用例/bird-ca-schools-15/spec.md",
          "line_start": 193,
          "line_end": 193,
          "sha256": "1dacc22e77955d987ee29b1fbeb997899e30ee0c22264a861033681beb547d26",
          "quote": "| 再分发 | 本用例以 CC BY-SA 4.0 同源共享（含 `inputs/` 数据库与 `truth.json` 的 gold SQL） |"
        }
      ],
      "upstream_version": {"status": "unknown", "value": null},
      "upstream_terms": {
        "status": "not_locally_verified", "original_license_url": null,
        "local_copy": null, "sha256": null,
        "notice_status": "not_locally_verified", "notice_local_copy": null, "notice_sha256": null
      },
      "remaining_boundaries": [
        "既有spec另载数据库发行快照差异；本表unknown仅指未核定与许可正文绑定的上游版本或commit，不抹去既有快照记载。",
        "本表转录CC BY-SA再分发声明，不认证原始授权链、全部条款已满足或法律合规。"
      ]
    },
    {
      "case_id": "dabstep-payments-10",
      "source_parts": [
        {
          "name": "DABstep / Adyen and Hugging Face",
          "role": "benchmark_dataset_and_scorer",
          "url": "https://huggingface.co/datasets/adyen/DABstep",
          "declared_license": "CC-BY-4.0",
          "license_scope": "dataset_questions_and_imported_scorer_functions_as_declared"
        }
      ],
      "reuse_summary": "既有规格声明questions删除answer字段、6个context数据文件原样使用、任务书中文重写；官方scorer六函数移植，其余判分逻辑与文档自写。",
      "evidence": [
        {
          "path": "2-用例/dabstep-payments-10/spec.md",
          "line_start": 114,
          "line_end": 118,
          "sha256": "ef0f822d01b56089bb6fe56f1a9a6bcf7f4a1ee9796689908c8ac04a45c53852",
          "quote": "| 基准 | **DABstep: Data Agent Benchmark for Multi-Step Reasoning**（Adyen + Hugging Face） |\n| 数据集 | https://huggingface.co/datasets/adyen/DABstep （10 题取自 **dev** 划分，官方随包提供答案） |\n| 榜单/主页 | https://huggingface.co/spaces/adyen/DABstep |\n| 官方仓库 / 判分器 | https://huggingface.co/spaces/adyen/DABstep 内的 `dabstep_benchmark/evaluation/scorer.py`（GitHub 上同名 `adyen/DABstep` 仓已 404，勿引；本用例 checker.py 移植其 6 个函数并标注来源） |\n| 许可证 | **CC-BY-4.0** — https://creativecommons.org/licenses/by/4.0/ |"
        },
        {
          "path": "2-用例/dabstep-payments-10/spec.md",
          "line_start": 120,
          "line_end": 121,
          "sha256": "ef0f822d01b56089bb6fe56f1a9a6bcf7f4a1ee9796689908c8ac04a45c53852",
          "quote": "| 改写说明 | ① `questions.jsonl` 删除官方 `answer` 字段，仅保留 `task_id/question/guidelines/level`（英文原题保留原句并在此标注来源）；② 6 个 context 数据文件原样使用，未改一字；③ `instruction.md` 用中文重写任务书；④ checker.py 的 scorer 部分为官方实现移植（CC-BY-4.0），其余为自写。 |\n| 版权归属 | 数据与题面 © Adyen / Hugging Face，按 CC-BY-4.0 使用并署名；本用例判分逻辑与文档由 harness-compare-bench 编写。 |"
        }
      ],
      "upstream_version": {"status": "unknown", "value": null},
      "upstream_terms": {
        "status": "not_locally_verified", "original_license_url": null,
        "local_copy": null, "sha256": null,
        "notice_status": "not_locally_verified", "notice_local_copy": null, "notice_sha256": null
      },
      "remaining_boundaries": [
        "spec已有CC BY 4.0通用条款URL；本表original_license_url指与取得上游版本绑定的原始许可文件，未核定所以null。",
        "既有读取日期和来源地址不是本次已核完整条款或授权链的收据。"
      ]
    },
    {
      "case_id": "exercism-py-6",
      "source_parts": [
        {
          "name": "Aider polyglot-benchmark",
          "role": "benchmark_packaging",
          "url": "https://github.com/Aider-AI/polyglot-benchmark",
          "declared_license": "MIT",
          "license_scope": "benchmark_packaging_as_declared"
        },
        {
          "name": "Exercism Python track and problem-specifications",
          "role": "exercise_source",
          "url": "https://github.com/exercism/python",
          "declared_license": "MIT",
          "license_scope": "exercise_tests_and_skeletons_as_declared"
        }
      ],
      "reuse_summary": "既有规格声明6份官方测试与骨架原样保留；题面及README中文重写；checker与6份参考解本仓新写。测试数据来源另有Exercism problem-specifications，不能只归于Aider打包。",
      "evidence": [
        {
          "path": "2-用例/exercism-py-6/spec.md",
          "line_start": 91,
          "line_end": 98,
          "sha256": "1ae5102ebf4cf6fe0971f136ec536e438d977a56daa0e1bc20183ab06bead2c6",
          "quote": "- **来源**：Aider polyglot-benchmark（https://github.com/Aider-AI/polyglot-benchmark）中的 Python 练习题打包；上游为 **Exercism Python track**（https://github.com/exercism/python），测试数据来自 Exercism problem-specifications（https://github.com/exercism/problem-specifications）。\n- **许可证**：MIT License（Exercism 与 polyglot-benchmark 均为 MIT）。\n- **读取日期**：2026-10-22（素材取自本机已落盘的 polyglot-benchmark 快照，未联网）。\n- **是否改写**：\n  - 6 份官方测试（`*_test.py`）与骨架（`*.py`）**原样保留、未改写**（SHA-256 记录在 `truth.json`）；\n  - 题面 `instruction.md`、`spec.md`、各题 `README.md`、`inputs/README.md` 为中文重写（不整段照抄官方题面），保留关键约束与输入输出格式；\n  - `checker.py` 与 `solution/` 下 6 份参考解为本题库新写代码（仅标准库），参考解均已跑通官方测试。\n- **署名**：Exercises and tests © Exercism contributors, MIT License；benchmark packaging © Aider polyglot-benchmark contributors, MIT License。"
        }
      ],
      "upstream_version": {"status": "unknown", "value": null},
      "upstream_terms": {
        "status": "not_locally_verified", "original_license_url": null,
        "local_copy": null, "sha256": null,
        "notice_status": "not_locally_verified", "notice_local_copy": null, "notice_sha256": null
      },
      "remaining_boundaries": [
        "MIT是既有来源声明；本次未核与源版本绑定的完整许可和版权通知副本。",
        "本仓新写代码与中文文档不因上游MIT声明而自动取得整仓统一许可。"
      ]
    },
    {
      "case_id": "lcb-recent-hard-4",
      "source_parts": [
        {
          "name": "LiveCodeBench v6 repository",
          "role": "repository_code",
          "url": "https://github.com/LiveCodeBench/LiveCodeBench",
          "declared_license": "MIT",
          "license_scope": "livecodebench_repository_code_as_declared_not_atcoder_materials"
        },
        {
          "name": "AtCoder Beginner Contest original statements and tests",
          "role": "original_problem_source",
          "url": "https://atcoder.jp/contests/abc387/tasks/abc387_f",
          "declared_license": "not_established_by_cited_material",
          "license_scope": "original_problem_statements_and_tests_rights_not_established_here"
        }
      ],
      "reuse_summary": "既有规格声明LiveCodeBench题库的题面中文改写、测试原样使用、判分逻辑标准库重写；MIT明确标为LiveCodeBench仓库，AtCoder另为题面与测试原始出处且题面版权归AtCoder。",
      "evidence": [
        {
          "path": "2-用例/lcb-recent-hard-4/spec.md",
          "line_start": 93,
          "line_end": 105,
          "sha256": "65c1debb503fefe9f4e813be9f414cd859fc75063fa3670c838b250772a174b9",
          "quote": "| 题库来源 | **LiveCodeBench v6**（`code_generation_lite` 的 `test6.jsonl`，2025-01 窗口；官方仓库 <https://github.com/LiveCodeBench/LiveCodeBench>，HF <https://huggingface.co/datasets/livecodebench/code_generation_lite>） |\n| 许可证 | **MIT**（LiveCodeBench 仓库） |\n| 读取日期 | 2026-10-22（本机实拉后落 `/tmp/lcb_recent.jsonl`，抽取 hard 6 题中取 4 题） |\n| 是否改写 | **题面按中文重写**（保留输入/输出格式、约束、样例与样例解释），**非英文原文照抄**；测试数据（公开 + 私有）原样使用 |\n| 题目出处 | AtCoder Beginner Contest（题面与测试的原始出处，见下）；题面版权归 AtCoder，本用例仅作中文改写教学用 |\n| 判分器来源 | 移植 LiveCodeBench 官方评测的「逐测试 stdin 注入 + 超时 + 输出规整比较」口径，用 Python 标准库重写（MIT） |\n\n| problem_id | 题名 | 出处 | 日期 | URL | 公开/私有测试 |\n|---|---|---|---|---|---:|\n| `abc387_f` | Count Arrays | ABC387 F | 2025-01-04 | <https://atcoder.jp/contests/abc387/tasks/abc387_f> | 3 / 40 |\n| `abc388_f` | Dangerous Sugoroku | ABC388 F | 2025-01-11 | <https://atcoder.jp/contests/abc388/tasks/abc388_f> | 3 / 40 |\n| `abc388_g` | Simultaneous Kagamimochi 2 | ABC388 G | 2025-01-11 | <https://atcoder.jp/contests/abc388/tasks/abc388_g> | 2 / 40 |\n| `abc389_g` | Odd Even Graph | ABC389 G | 2025-01-18 | <https://atcoder.jp/contests/abc389/tasks/abc389_g> | 3 / 40 |"
        }
      ],
      "upstream_version": {"status": "unknown", "value": null},
      "upstream_terms": {
        "status": "not_locally_verified", "original_license_url": null,
        "local_copy": null, "sha256": null,
        "notice_status": "not_locally_verified", "notice_local_copy": null, "notice_sha256": null
      },
      "remaining_boundaries": [
        "AtCoder source_part URL为四题中abc387_f的既有原作链接代表，完整四题链接仍见同一spec第102至105行。",
        "LiveCodeBench仓库MIT声明不替AtCoder题面或测试授权；教学用途说明不是本次已核授权凭据。",
        "既有v6或题目日期不等于已核定原始许可文件的commit；AtCoder适用条款及上游完整通知仍待核。"
      ]
    },
    {
      "case_id": "tb-cargo-plan",
      "source_parts": [
        {
          "name": "Terminal-Bench cargo-flight-dispatch",
          "role": "upstream_task",
          "url": "https://github.com/harbor-framework/terminal-bench",
          "declared_license": "Apache-2.0",
          "license_scope": "upstream_task_reference_implementation_and_assertions_as_declared"
        }
      ],
      "reuse_summary": "既有规格声明去Docker/uv/pytest、断言移植到标准库、题面中文化和输出路径调整；参考实现与27项断言移植自上游tests/test_outputs.py，原件留档于reference。",
      "evidence": [
        {
          "path": "2-用例/tb-cargo-plan/spec.md",
          "line_start": 78,
          "line_end": 80,
          "sha256": "8a94143a8333254fe5e57f7d47ea3708bd7837dd674c4189343c245f514758ea",
          "quote": "- 题目：Terminal-Bench `cargo-flight-dispatch`，https://github.com/harbor-framework/terminal-bench ，**Apache-2.0**，读取日期 2026-10-22；\n- 改造：去 Docker/uv/pytest（断言移植为 stdlib），题面中文化重写，输出路径改为运行目录相对路径；\n- 参考实现（haversine / 风三角 / ISA 密度 / 侧风）与 27 项断言移植自官方 `tests/test_outputs.py`（同许可），原件留档于 `reference/`。"
        }
      ],
      "upstream_version": {"status": "unknown", "value": null},
      "upstream_terms": {
        "status": "not_locally_verified", "original_license_url": null,
        "local_copy": null, "sha256": null,
        "notice_status": "not_locally_verified", "notice_local_copy": null, "notice_sha256": null
      },
      "remaining_boundaries": [
        "Apache-2.0及改造范围按既有spec转录，不认证所有上游版权或NOTICE保留义务已完成。",
        "本次未核取得该任务版本的commit及其完整许可和通知副本。"
      ]
    }
  ],
  "original_assets": {
    "license_status": "not_selected",
    "license": null,
    "decision_by": "repository_owner",
    "decision_status": "owner_decision_required",
    "scope": ["original_tools", "original_reports_and_documents"],
    "third_party_excluded": true
  },
  "license_grant": {
    "new_license_granted": false,
    "legal_compliance_certified": false
  },
  "limits": [
    "仅集中五案例既有来源与许可声明，不是全仓资产或法律合规审计。",
    "固定文件SHA与逐行引文证明本地公开文本可追，不证明原始授权主体、权利链或上游许可适用性。",
    "完整上游条款与NOTICE未本地核验，版本绑定URL、commit及副本SHA未知时保持null。",
    "原创工具和报告的统一许可仍待维护者选择；本索引不授新权利，不以unknown代替已开源授权。",
    "本索引不覆盖产品输出、第三方对话轨迹、个人数据或全部历史代码的再授权。",
    "不修改旧用例、判卷、gold、历史成绩、正式25格、轨道或样本量。"
  ]
}''')
MAX_BYTES = 200000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def same(actual, expected, label='index'):
    """Exact recursive types and values: True, 1 and 1.0 never alias."""
    require(type(actual) is type(expected), label + ': type mismatch')
    if type(expected) is dict:
        require(actual.keys() == expected.keys(), label + ': keys mismatch')
        for key in expected:
            same(actual[key], expected[key], label + '.' + key)
    elif type(expected) is list:
        require(len(actual) == len(expected), label + ': length mismatch')
        for i, (left, right) in enumerate(zip(actual, expected)):
            same(left, right, label + '[' + str(i) + ']')
    else:
        require(actual == expected, label + ': value mismatch')


def parse_json(raw):
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key: ' + key)
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError('nonfinite JSON constant: ' + value)

    def finite(value):
        if type(value) is float:
            require(math.isfinite(value), 'nonfinite JSON number')
        elif type(value) is dict:
            for child in value.values():
                finite(child)
        elif type(value) is list:
            for child in value:
                finite(child)

    value = json.loads(raw.decode('utf-8'), object_pairs_hook=object_pairs,
                       parse_constant=invalid_constant)
    finite(value)
    return value


def safe_file(root: Path, relative: str) -> Path:
    require(type(relative) is str and bool(relative), 'invalid relative path type')
    path = PurePosixPath(relative)
    require(not path.is_absolute() and '\\' not in relative and
            str(path) == relative and all(part not in ('', '.', '..') for part in relative.split('/')),
            'noncanonical relative path: ' + relative)
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(), 'invalid root directory')
    current = root
    for part in path.parts:
        current = current / part
        require(not current.is_symlink(), 'symlink path: ' + relative)
    require(current.is_file(), 'missing regular file: ' + relative)
    require(root.resolve() in current.resolve().parents, 'path escapes root: ' + relative)
    return current


def read_pinned(root, relative, expected, category):
    path = safe_file(root, relative)
    with path.open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, 'document byte budget exceeded: ' + relative)
    require(hashlib.sha256(raw).hexdigest() == expected, category + ' hash mismatch: ' + relative)
    return raw


def validate_index(index) -> dict:
    """Pure frozen factual contract, independent of file hashes and filesystem.
    This is exact declaration/unknown preservation, not a legal decision engine.
    EXPECTED_INDEX is independently frozen code data, never loaded from the input.
    """
    require(type(EXPECTED_INDEX) is dict, 'index contract not frozen')
    same(index, EXPECTED_INDEX)
    return {
        'status': 'PASS_FROZEN_DECLARATION_INDEX',
        'case_count': len(index['cases']),
        'case_ids': [case['case_id'] for case in index['cases']],
        'new_license_granted': False,
        'legal_compliance_certified': False,
        'original_asset_license_status': 'not_selected',
        'upstream_terms_locally_verified': False,
    }


def check_evidence(index, raw_sources):
    for case in index['cases']:
        for evidence in case['evidence']:
            path = evidence['path']
            require(path in SOURCE_PINS, 'unregistered evidence source')
            same(evidence['sha256'], SOURCE_PINS[path], 'evidence SHA')
            start, end = evidence['line_start'], evidence['line_end']
            require(type(start) is int and type(end) is int and 1 <= start <= end,
                    'invalid evidence line range')
            lines = raw_sources[path].decode('utf-8').splitlines()
            require(end <= len(lines), 'evidence line range outside source')
            same(evidence['quote'], '\n'.join(lines[start-1:end]), 'evidence quote')


def derive(root: Path) -> dict:
    """Read only pinned new documents first, then five existing specifications."""
    require(type(DOCUMENT_PINS) is dict, 'document pins not frozen')
    documents = {path: read_pinned(root, path, sha, 'document')
                 for path, sha in DOCUMENT_PINS.items()}
    sources = {path: read_pinned(root, path, sha, 'source')
               for path, sha in SOURCE_PINS.items()}
    index = parse_json(documents[BASE + 'sources.json'])
    result = validate_index(index)
    check_evidence(index, sources)
    result['pinned_document_count'] = len(documents) + len(sources)
    result['source_sha256'] = dict(DOCUMENT_PINS, **SOURCE_PINS)
    result['limits'] = list(index['limits'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    try:
        result = derive(args.root)
    except (ValueError, OSError, UnicodeError, RecursionError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({'ok': True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
