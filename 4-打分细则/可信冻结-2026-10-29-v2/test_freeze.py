#!/usr/bin/env python3
"""Synthetic schema/negative tests, not product executions or grader assertions."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("freeze", Path(__file__).with_name("freeze.py"))
f = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(f)
REAL = Path(__file__).resolve().parents[2]


class FreezeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = f.load(REAL / f.BASE / "config.json")
        cp = self.config["case_snapshots"][f.CASES[0]]
        values = dict(case_version=cp["case_version"], product_version="synthetic-v1", model="deepseek-flash", route=dict(host='api.deepseek.com',provider_id='synthetic-local-provider',wire_protocol='responses',endpoint='https://api.deepseek.com/responses'), tools=["bash"], permissions="isolated", skills="off", started_at="2026-10-29T12:00:00+08:00", finished_at="2026-10-29T12:01:00+08:00", evidence_grade="synthetic-complete", final_adjudication="valid", rule_version=f.RULE, checker_sha256=cp["checker.py"], truth_sha256=cp["truth.json"], case_sha256=cp["manifest_sha256"])
        self.e = dict(event_id="SYNTHETIC-FIRST", category="product_run", product="codex", group="A_same_model", experiment=False, case_id=f.CASES[0], facts={k:f.fact(v,ptr="/facts/"+k) for k,v in values.items()}, gates={k:f.fact(True,ptr="/gates/"+k) for k in f.GATES}, score=f.fact(dict(earned=15,possible=15,assessed=15,reported=100,reward=1,rule_version=f.RULE,checker_sha256=cp["checker.py"]),ptr="/score"), selection=dict(plan_id="SYNTHETIC-PLAN",slot_id="cell1",order=1,kind="first",parent_id=None,reason="fixed_first",registered_at="2026-10-29T11:30:00+08:00",plan_source=1,plan_pointer="/registrations/0"), sources=[],issues=[],collected_at="2026-10-29T12:02:00+08:00",original_time=f.fact(values["started_at"],ptr="/facts/started_at"))
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
        self.e["selection"]["registered_at"]="2026-10-29T12:00:30+08:00";self.sync()
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
