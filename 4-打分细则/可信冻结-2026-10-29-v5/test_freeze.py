#!/usr/bin/env python3
"""Synthetic schema/negative tests, not product executions or grader assertions.

v5 适配（freeze-20261029-v5，2026-10-31）：合成（temp-root）断言与 v4 逐字节相同；REAL 树断言按
v5 真相改写——
(a) v5 lock 无任何 work-registry-live pin + pin 卫生断言（本地缺失文件不入 pin、活登记未知登记不入 pin；继承 v4）；
(b) 六账计数保持 registry∪imports∪历史 动态并集断言（v4 封印修订-1 定型，build 后门）；
(c) official 表断言改为结果鲁棒式：B_native 只能是空或恰 formal-b2 唯一注册产品行，b2 产品行必居
groups/rejected 之一（吸取 v4 封印修订-1「预写未知终局」教训，封印时不预写运行结果）。
差异逐条见本目录 README.md「与 v4 的差异」。
"""
import copy
import datetime as _dt
import importlib.util
import re
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("freeze", Path(__file__).with_name("freeze.py"))
f = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(f)
REAL = Path(__file__).resolve().parents[2]


def validate_against_schema(inst, schema, defs, path="$"):
    """L3-A2：对 $defs 子集的 JSON Schema 校验（stdlib 实现该 schema 实际使用的关键字）。

    支持：$ref(#/$defs/名)、type(object/string)、required、additionalProperties:false、
    properties、enum、const、pattern、format:date-time（须带时区）。
    """
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return validate_against_schema(inst, defs[name], defs, path)
    if "enum" in schema:
        assert inst in schema["enum"], f"{path}: {inst!r} not in enum"
    if "const" in schema:
        assert inst == schema["const"], f"{path}: {inst!r} != const"
    t = schema.get("type")
    if t == "object":
        assert isinstance(inst, dict), f"{path}: not object"
        for k in schema.get("required", []):
            assert k in inst, f"{path}: missing required {k}"
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = set(inst) - set(props)
            assert not extra, f"{path}: unexpected properties {sorted(extra)}"
        for k, sub in props.items():
            if k in inst:
                validate_against_schema(inst[k], sub, defs, f"{path}/{k}")
    elif t == "string":
        assert isinstance(inst, str), f"{path}: not string"
        if "pattern" in schema:
            assert re.search(schema["pattern"], inst), f"{path}: pattern miss: {inst!r}"
        if schema.get("format") == "date-time":
            d = _dt.datetime.fromisoformat(inst.replace("Z", "+00:00"))
            assert d.tzinfo is not None, f"{path}: date-time without timezone: {inst!r}"


class FreezeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = f.load(REAL / f.BASE / "config.json")
        # v3: 夹具时刻从本代 effective_at 动态推导（历史行不在冻结期，合成行必须在期内）
        _base = _dt.datetime.fromisoformat(self.config["effective_at"])
        _t = lambda m: (_base + _dt.timedelta(minutes=m)).isoformat(timespec="seconds")
        _REG, _START, _FIN, _COLL = _t(30), _t(60), _t(61), _t(62)
        self._t = _t
        cp = self.config["case_snapshots"][f.CASES[0]]
        values = dict(case_version=cp["case_version"], product_version="synthetic-v1", model="deepseek-flash", route=dict(host='api.deepseek.com',provider_id='synthetic-local-provider',wire_protocol='responses',endpoint='https://api.deepseek.com/responses'), tools=["bash"], permissions="isolated", skills="off", started_at=_START, finished_at=_FIN, evidence_grade="synthetic-complete", final_adjudication="valid", rule_version=f.RULE, checker_sha256=cp["checker.py"], truth_sha256=cp["truth.json"], case_sha256=cp["manifest_sha256"])
        self.e = dict(event_id="SYNTHETIC-FIRST", category="product_run", product="codex", group="A_same_model", experiment=False, case_id=f.CASES[0], facts={k:f.fact(v,ptr="/facts/"+k) for k,v in values.items()}, gates={k:f.fact(True,ptr="/gates/"+k) for k in f.GATES}, score=f.fact(dict(earned=15,possible=15,assessed=15,reported=100,reward=1,rule_version=f.RULE,checker_sha256=cp["checker.py"]),ptr="/score"), selection=dict(plan_id="SYNTHETIC-PLAN",slot_id="cell1",order=1,kind="first",parent_id=None,reason="fixed_first",registered_at=_REG,plan_source=1,plan_pointer="/registrations/0"), sources=[],issues=[],collected_at=_COLL,original_time=f.fact(values["started_at"],ptr="/facts/started_at"))
        self.identity = {k:self.e[k] for k in ("event_id","category","product","group","experiment","case_id")}
        self.identity["run_id"] = "synthetic-original-run-1"
        self.e["identity"] = f.fact(self.identity,ptr="/identity")
        self.sync()

    def sync(self):
        proof = {"identity":self.e["identity"]["value"],"facts":{k:v["value"] for k,v in self.e["facts"].items()},"gates":{k:v["value"] for k,v in self.e["gates"].items()},"score":self.e["score"]["value"],"note":"synthetic test only"}
        (self.root/"proof.json").write_text(f.dump(proof))
        sel = self.e["selection"]
        registration={"event_id":self.e["event_id"],**{k:v for k,v in sel.items() if k not in ("plan_source","plan_pointer")}}
        (self.root/"plan.json").write_text(f.dump({"registrations":[registration]}))
        self.e["sources"]=[f.pin(self.root,"proof.json"),f.pin(self.root,"plan.json")]
        key="|".join(self.e[k] for k in ("group","product","case_id"))
        self.config["official_slots"]={key:dict(plan_id=sel["plan_id"],slot_id=sel["slot_id"],plan_sha256=self.e["sources"][1]["sha256"])}

    def valid(self):
        f.validate_event(self.e,self.root,{})
        f.select_events([self.e])
        f.validate_plan_completeness([self.e],self.root,{})

    def test_positive_complete_synthetic(self):
        self.valid();self.assertEqual(f.reasons(self.e,self.config),[])

    def test_missing_field(self):
        del self.e["facts"]["permissions"]
        with self.assertRaises(f.Invalid):self.valid()

    def test_unexpected_field(self):
        self.e["allow_partial"]=True
        with self.assertRaises(f.Invalid):self.valid()

    def test_wrong_fact_pointer(self):
        self.e["facts"]["model"]["refs"][0]["pointer"]="/facts/tools"
        with self.assertRaises(f.Invalid):self.valid()

    def test_hash_drift(self):
        (self.root/"proof.json").write_text('{}')
        with self.assertRaises(f.Invalid):self.valid()

    def test_contamination(self):
        self.e["gates"]["contamination_free"]["value"]=False;self.sync();self.valid()
        self.assertIn("gate:contamination_free",f.reasons(self.e,self.config))

    def test_case_invalid(self):
        self.e["gates"]["case_valid"]["value"]=False;self.sync();self.valid()
        self.assertIn("gate:case_valid",f.reasons(self.e,self.config))

    def test_version_unfrozen(self):
        self.e["facts"]["rule_version"]["value"]="draft";self.sync();self.valid()
        self.assertIn("rule_version_not_frozen",f.reasons(self.e,self.config))

    def test_case_version_identity(self):
        self.e["facts"]["case_version"]["value"]="random-known-v1";self.sync();self.valid()
        self.assertIn("case_version_identity_mismatch",f.reasons(self.e,self.config))

    def test_duplicate_event_id(self):
        with self.assertRaises(f.Invalid):f.select_events([self.e,self.e])

    def test_original_run_id_alias(self):
        e2=copy.deepcopy(self.e);e2["event_id"]="different-event-id"
        with self.assertRaises(f.Invalid):f.select_events([self.e,e2])

    def test_identity_variant_tamper(self):
        self.e["experiment"]=True
        with self.assertRaises(f.Invalid):self.valid()

    def test_research_variant_never_official(self):
        self.e["experiment"]=True;self.e["identity"]["value"]["experiment"]=True;self.sync();self.valid()
        self.assertIn("research_variant_not_official_product",f.reasons(self.e,self.config))

    def test_same_model_wrong_upstream_route(self):
        self.e['facts']['route']['value'].update(host='third-party.example',endpoint='https://third-party.example/responses');self.sync();self.valid()
        self.assertIn('official_upstream_route_not_proven',f.reasons(self.e,self.config))

    def test_route_host_endpoint_contradiction(self):
        self.e['facts']['route']['value']['endpoint']='https://third-party.example/responses';self.sync()
        with self.assertRaises(f.Invalid):self.valid()

    def test_invalid_adjudication_even_with_all_gates_true(self):
        self.e['facts']['final_adjudication']['value']='invalid';self.sync();self.valid()
        self.assertIn('final_adjudication_not_valid',f.reasons(self.e,self.config))

    def test_mixed_product_group(self):
        self.e["product"]="yuanbao";self.e["identity"]["value"]["product"]="yuanbao";self.sync();self.valid()
        self.assertIn("group_product_mismatch",f.reasons(self.e,self.config))

    def test_alternate_plan_cannot_restart_first(self):
        self.config["official_slots"]={}
        self.assertIn("not_canonical_official_slot",f.reasons(self.e,self.config))

    def managed_unknown(self, fields):
        self.e['issues'] = [dict(id='managed-unknown',unknown_fields=fields,knowledge_status='unknown',investigation_status='stopped',confound_status='not_excluded',impact='missing evidence blocks admission, not product failure',next_step='obtain original receipt',stop_condition='no original public evidence',reopen_condition='new original receipt',refs=[dict(source=0,pointer='/note')])]

    def test_unknown_without_issue_rejected(self):
        self.e['score']=f.fact();self.sync()
        with self.assertRaises(f.Invalid):self.valid()

    def test_unknown_is_null_not_zero(self):
        self.e["score"]=f.fact();self.managed_unknown(['score']);self.sync();self.valid()
        self.assertIsNone(self.e["score"]["value"])
        self.assertIn("no_reviewable_score",f.reasons(self.e,self.config))

    def test_unknown_cannot_smuggle_value(self):
        self.e["score"]["state"]="unknown"
        with self.assertRaises(f.Invalid):self.valid()

    def test_full_case_denominator_required(self):
        self.e['score']['value'].update(earned=5,possible=5,assessed=5,reported=100);self.sync();self.valid()
        self.assertIn('score_denominator_not_full_case_contract',f.reasons(self.e,self.config))

    def test_no_assessed_subset_rescaling(self):
        self.e["score"]["value"].update(earned=5,possible=10,assessed=5,reported=100,reward=None);self.sync()
        with self.assertRaises(f.Invalid):self.valid()

    def test_partial_score_remains_partial(self):
        self.e["score"]["value"].update(earned=5,possible=10,assessed=5,reported=50,reward=None);self.sync();self.valid()
        self.assertIn("score_incomplete_no_rescale",f.reasons(self.e,self.config))

    def test_partial_score_cannot_have_reward(self):
        self.e["score"]["value"].update(earned=5,possible=10,assessed=5,reported=50,reward=1);self.sync()
        with self.assertRaises(f.Invalid):self.valid()

    def test_outcome_based_registration(self):
        self.e["selection"]["registered_at"]=self._t(61);self.sync()
        with self.assertRaises(f.Invalid):self.valid()

    def test_retry_after_valid_result(self):
        retry=copy.deepcopy(self.e);retry["event_id"]="retry";retry["identity"]["value"]["run_id"]="synthetic-retry";retry["selection"].update(order=2,kind="retry",parent_id=self.e["event_id"],reason="transport_error")
        with self.assertRaises(f.Invalid):f.select_events([self.e,retry])

    def test_retry_cherry_picking(self):
        self.e["facts"]["final_adjudication"]["value"]="infrastructure_invalid"
        retry=copy.deepcopy(self.e);retry["event_id"]="retry";retry["identity"]["value"]["run_id"]="synthetic-retry";retry["selection"].update(order=2,kind="retry",parent_id=self.e["event_id"],reason="score_low")
        with self.assertRaises(f.Invalid):f.select_events([self.e,retry])

    def test_replacement_of_valid_attempt(self):
        e=copy.deepcopy(self.e);e["event_id"]="replace";e["identity"]["value"]["run_id"]="synthetic-replace";e["selection"].update(order=2,kind="replacement",parent_id=self.e["event_id"],reason="contamination")
        with self.assertRaises(f.Invalid):f.select_events([self.e,e])

    def test_replacement_cap(self):
        self.e['facts']['final_adjudication']['value']='invalid'
        r1=copy.deepcopy(self.e);r1['event_id']='r1';r1['identity']['value']['run_id']='run-r1';r1['selection'].update(order=2,kind='replacement',parent_id=self.e['event_id'],reason='contamination')
        r2=copy.deepcopy(r1);r2['event_id']='r2';r2['identity']['value']['run_id']='run-r2';r2['selection'].update(order=3,parent_id='r1')
        with self.assertRaises(f.Invalid):f.select_events([self.e,r1,r2])

    def test_omitted_registered_attempt(self):
        p=f.load(self.root/"plan.json");other=copy.deepcopy(p["registrations"][0]);other["event_id"]="missing-attempt";p["registrations"].append(other);(self.root/"plan.json").write_text(f.dump(p));self.e["sources"][1]=f.pin(self.root,"plan.json")
        with self.assertRaises(f.Invalid):f.validate_plan_completeness([self.e],self.root,{})

    def test_issue_axes(self):
        issue=dict(id="x",knowledge_status="unknown",investigation_status="stopped",confound_status="excluded",impact="x",next_step="x",stop_condition="x",reopen_condition="new original evidence",refs=[dict(source=0,pointer="/note")])
        with self.assertRaises(f.Invalid):f.validate_issues([issue])
        issue["confound_status"]="not_excluded";f.validate_issues([issue])

    def test_issue_requires_reopen_condition(self):
        with self.assertRaises(f.Invalid):f.validate_issues([{}])

    def test_path_escape(self):
        with self.assertRaises(f.Invalid):f.public_path(self.root,"../secret")

    def test_sealed_config_tamper(self):
        b=self.root/f.BASE;b.mkdir(parents=True);(b/"config.json").write_text('{}')
        (b/"freeze.lock.json").write_text(f.dump(dict(rule_version=f.RULE,pins=[f.pin(self.root,f.BASE+'/config.json')],trust_boundary="test")))
        (b/"config.json").write_text('{"changed":true}')
        with self.assertRaises(f.Invalid):f.verify_seal(self.root)

    def test_full_inputs_manifest_drift(self):
        c=self.root/'2-用例'/f.CASES[0];(c/'inputs').mkdir(parents=True)
        for n in ('instruction.md','spec.md','case.json','truth.json','checker.py'):(c/n).write_text(n)
        (c/'inputs'/'data.txt').write_text('one')
        old=f.snapshot_case(self.root,f.CASES[0]);(c/'inputs'/'data.txt').write_text('two')
        new=f.snapshot_case(self.root,f.CASES[0]);self.assertNotEqual(old['manifest_sha256'],new['manifest_sha256']);self.assertEqual(old['instruction.md'],new['instruction.md'])

    def test_duplicate_json_keys(self):
        (self.root/'duplicate.json').write_text('{"x":1,"x":2}')
        with self.assertRaises(f.Invalid):f.load(self.root/'duplicate.json')

    def test_dab2697_is_not_inferred_capability(self):
        self.assertEqual(f.SAFE_POLICY['dab2697'],'not_capability_attribution')

    # ---- v3 扩展：pin_class / 活台账 / 7 收据入六账 ----

    def _lock_drifts(self, pins):
        lock = dict(rule_version=f.RULE, pins=pins, trust_boundary="synthetic")
        b = self.root / f.BASE
        b.mkdir(parents=True, exist_ok=True)
        (b / "freeze.lock.json").write_text(f.dump(lock))
        return lock

    def test_live_doc_pin_drift_reported_not_fatal(self):
        # live_doc pin 字节漂移 → 进 drift 列表，不 raise（exit=0 语义的引擎层基础）
        (self.root / "doc.md").write_text("sealed")
        pin = f.pin(self.root, "doc.md"); pin["pin_class"] = "live_doc"
        self._lock_drifts([pin])
        (self.root / "doc.md").write_text("drifted")
        lock = f.load(self.root / f.BASE / "freeze.lock.json")
        contract_errors, drifts = f.lock_drifts(self.root, lock)
        self.assertEqual(contract_errors, [])
        self.assertEqual([d["path"] for d in drifts], ["doc.md"])
        self.assertEqual(drifts[0]["actual_sha256"], f.digest(b"drifted"))

    def test_contract_pin_drift_fails(self):
        # contract pin 字节漂移 → contract 错误，verify_seal 必须 raise（exit≠0 语义不变）
        (self.root / "input.json").write_text("sealed")
        pin = f.pin(self.root, "input.json"); pin["pin_class"] = "contract"
        self._lock_drifts([pin])
        (self.root / "input.json").write_text("drifted")
        lock = f.load(self.root / f.BASE / "freeze.lock.json")
        contract_errors, drifts = f.lock_drifts(self.root, lock)
        self.assertEqual(len(contract_errors), 1)
        self.assertEqual(drifts, [])
        with self.assertRaises(f.Invalid):
            f.verify_seal(self.root)

    def test_missing_live_doc_pin_is_drift_not_crash(self):
        pin = {"path": "gone.md", "sha256": "0" * 64, "pin_class": "live_doc"}
        self._lock_drifts([pin])
        contract_errors, drifts = f.lock_drifts(self.root, f.load(self.root / f.BASE / "freeze.lock.json"))
        self.assertEqual(contract_errors, [])
        self.assertEqual(drifts[0]["actual_sha256"], None)

    # ---- v5 适配：lock pin 卫生 / config schema 代际一致性 / 六账动态计数 / official 表 ----
    # v3 专属「work-registry-live.json 活台账」断言组在 v4 整体退役：v4 目录无活台账，差异见 README。

    def test_v5_lock_has_no_work_registry_live_pin(self):
        # (a) v5 lock 无任何 work-registry-live pin；pin 卫生：本地缺失文件一律不入 pin（v3 曾因隐私
        # 整理出现缺失/漂移 pin）；活登记未知登记.json 不入 pin（append-only，防条目追加造成封印漂移）
        lock = f.load(REAL / f.BASE / "freeze.lock.json")
        pinned = {x["path"]: x.get("pin_class", "contract") for x in lock["pins"]}
        self.assertFalse(any("work-registry-live" in p for p in pinned),
                         "v5 lock 不得含任何 work-registry-live pin")
        for path in pinned:
            self.assertTrue((REAL / path).is_file(), "pin 指向本地缺失文件: " + path)
        self.assertNotIn("5-评测报告/未知登记.json", pinned)

    def test_v5_config_matches_generational_schema(self):
        # v5 代际元数据一致性：真实 config.json 必须通过本代 config-schema.json（$id/rule_version const=v5）
        schema = f.load(REAL / f.BASE / "config-schema.json")
        validate_against_schema(f.load(REAL / f.BASE / "config.json"), schema, schema["$defs"])
        self.assertEqual(schema["$id"], "freeze-20261029-v5/config")
        self.assertEqual(schema["properties"]["rule_version"]["const"], f.RULE)

    @unittest.skipUnless((REAL / f.OUT).is_dir(), "OUT 未生成（build 后门；封印纪律：不预生成产物）")
    def test_v5_six_ledgers_counts_match_registry(self):
        # (b) 非产品类六账 = v2 registry 事件 ∪ 本代 imports 非产品事件，逐 event_id 恰一次
        # 逻辑继承 v4 封印修订-1 定型的动态并集断言（本代 imports：formal-b2 预检/自测非产品事件）。
        reg = f.load(REAL / "4-打分细则/可信冻结-2026-10-29-v2/work-registry.json")
        out = REAL / f.OUT
        path = next((p for p in (out / "six-ledgers.json", out / "six-ledgers.public-derived.json") if p.is_file()), None)
        self.assertIsNotNone(path, "six-ledgers 未生成（build 后门）")
        led = f.load(path)
        recipe = f.load(out / "build-recipe.json")
        import_ids = {}
        for s in recipe["imports"]:
            for e in f.load(REAL / s["path"])["events"]:
                import_ids.setdefault(e["category"], []).append(e["event_id"])
        registry_ids = {e["event_id"] for e in reg["events"]}
        ledger = f.load(REAL / f.LEDGER)
        hist_by_cat = {"product_run": [], "bare_model_probe": []}
        for r in ledger["runs"]:
            hist_by_cat["bare_model_probe" if r["product"] == "bare" else "product_run"].append("history:" + r["run_id"])
        for cat in ("self_test", "interface_preflight", "offline_recompute", "grading_regression", "bare_model_probe", "product_run"):
            expected = ([e["event_id"] for e in reg["events"] if e["category"] == cat]
                        + import_ids.get(cat, []) + hist_by_cat.get(cat, []))
            ids = [e["event_id"] for e in led[cat]]
            self.assertEqual(sorted(ids), sorted(expected), cat + " 计数须等于 历史∪registry∪imports 动态并集")
            for eid in set(expected):
                self.assertEqual(ids.count(eid), 1, eid + " missing/duplicated in " + cat)
        self.assertEqual([e for e in led["product_run"] if e["event_id"] in registry_ids], [],
                         "v2 registry 不含 product_run 事件（build 管道既有约束）")

    @unittest.skipUnless((REAL / f.OUT).is_dir(), "OUT 未生成（build 后门；封印纪律：不预生成产物）")
    def test_v5_official_groups_after_build(self):
        # 「不重新准入历史/v4 行」的 v5 等价断言（结果鲁棒式，吸取 v4 封印修订-1 教训：封印时不预写
        # 未知运行终局）——B_native 只能是空或恰 b2 唯一注册产品行；b2 产品行必居 groups/rejected 之一；
        # 两个非产品事件必按类别拒绝；96 条历史行全 rejected；v4 行不在本代候选（不重判不重准入）。
        b2_prod = "formal-b2-doubao-exercism-py-6-01"
        out = REAL / f.OUT
        path = next((p for p in (out / "official-main-table.json", out / "official-main-table.public-derived.json") if p.is_file()), None)
        self.assertIsNotNone(path, "official-main-table 未生成（build 后门）")
        t = f.load(path)
        self.assertEqual(t["rule_version"], f.RULE)
        self.assertEqual(sorted(t["groups"]["A_same_model"]), [], "A_same_model 必须为空（v5 不准入 A 组历史）")
        b = sorted(t["groups"]["B_native"])
        self.assertIn(b, ([], [b2_prod]), "B_native 只能是空或恰 b2 唯一产品行（不重新准入任何历史/v4 行）")
        rej = {r["event_id"]: r["reasons"] for r in t["rejected"] if r["event_id"].startswith("formal-b2-")}
        if b == [b2_prod]:
            self.assertNotIn(b2_prod, rej, "b2 产品行已准入则不得同时出现在 rejected")
        else:
            self.assertIn(b2_prod, rej, "b2 产品行未准入则必须以合规理由出现在 rejected")
        for nonprod in ("formal-b2-doubao-preflight-01", "formal-b2-checker-selftest-01"):
            self.assertIn("not_product_run", rej[nonprod], nonprod + " 非产品事件按类别拒绝")
        self.assertEqual(len([r for r in t["rejected"] if r["event_id"].startswith("history:")]), 96,
                         "96 条历史行全部 rejected 且含 historical 理由")
        self.assertEqual(len([r for r in t["rejected"] if r["event_id"].startswith("formal-b1-")]), 0,
                         "v5 候选不含 v4 行（不重判不重准入）")

    # ---- L3-A4：pin_class 机械归类（读取面引用路径必为 contract；错标样本必红） ----

    def _classification_fixture(self, config_pin_class, pin_registry_source):
        c = {"historical_ledger": {"path": "in/hist.json", "sha256": "0" * 64},
             "work_registry": {"path": "in/registry.json", "sha256": "0" * 64}}
        (self.root / f.BASE).mkdir(parents=True, exist_ok=True)
        (self.root / f.BASE / "config.json").write_text("{}\n")
        (self.root / "in").mkdir(parents=True, exist_ok=True)
        (self.root / "in" / "hist.json").write_text("{}\n")
        reg = {"schema_version": 1, "coverage": {"cutoff": "2026-10-29T00:00:00+08:00"},
               "events": [{"event_id": "work:syn", "category": "self_test",
                           "source": {"path": "in/receipt.txt", "sha256": "0" * 64},
                           "locator": "l", "description": "d"}]}
        (self.root / "in" / "registry.json").write_text(f.dump(reg))
        (self.root / "in" / "receipt.txt").write_text("receipt\n")
        lock_pins = [{"path": f.BASE + "/config.json", "sha256": "0" * 64, "pin_class": config_pin_class},
                     {"path": "in/hist.json", "sha256": "0" * 64, "pin_class": "contract"},
                     {"path": "in/registry.json", "sha256": "0" * 64, "pin_class": "contract"}]
        if pin_registry_source:
            lock_pins.append({"path": "in/receipt.txt", "sha256": "0" * 64, "pin_class": "contract"})
        lock = dict(rule_version=f.RULE, pins=lock_pins, trust_boundary="synthetic")
        return c, lock

    def test_read_surface_misclassified_pin_is_red(self):
        # 错标样本：config.json 被 lock 标为 live_doc → 机械归类必抓（verify_seal 会硬失败）
        c, lock = self._classification_fixture("live_doc", True)
        viol = f.check_pin_classification(self.root, lock, c)
        self.assertTrue(any(v["path"] == f.BASE + "/config.json" and v["pin_class"] == "live_doc" for v in viol))

    def test_read_surface_correct_labels_green(self):
        c, lock = self._classification_fixture("contract", True)
        self.assertEqual(f.check_pin_classification(self.root, lock, c), [])

    def test_read_surface_registry_source_must_be_pinned(self):
        # registry 事件 source 是读取面一部分：漏 pin（not-pinned）= 违规
        c, lock = self._classification_fixture("contract", False)
        viol = f.check_pin_classification(self.root, lock, c)
        self.assertTrue(any(v["path"] == "in/receipt.txt" and v["pin_class"] == "not-pinned" for v in viol))


    def test_real_v5_read_surface_all_contract(self):
        # 真实 v5：读取面全部本地路径均为 contract pin（verify_seal 硬自检的静态等价断言）
        lock = f.load(REAL / f.BASE / "freeze.lock.json")
        c = f.load(REAL / f.BASE / "config.json")
        self.assertEqual(f.check_pin_classification(REAL, lock, c), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
