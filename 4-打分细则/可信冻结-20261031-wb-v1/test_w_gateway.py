#!/usr/bin/env python3
"""Offline synthetic tests only. No model, desktop or product-run data."""
import copy
import unittest
import test_freeze as legacy
f, REAL = legacy.f, legacy.REAL


class GatewayTests(legacy.FreezeTests):
    def setUp(self):
        super().setUp()
        self.e.update(product='workbuddy', group='W_gateway')
        self.e['identity']['value'].update(product='workbuddy', group='W_gateway')
        self.e['facts']['model']['value'] = copy.deepcopy(f.W_MODEL)
        self.e['facts']['route']['value'].update(host='nonofficial.example', endpoint='https://nonofficial.example/responses')
        self.e['issues'] = [dict(id='backend-model-unverified', attribution_scope='same_model_attribution', unknown_fields=[], knowledge_status='unknown', investigation_status='stopped', confound_status='not_excluded', impact='Backend model identity and parameter mapping are not proven; product-only observation, not same-model causality.', next_step='Obtain independently reviewable upstream attestation before same-model claims.', stop_condition='No upstream identity attestation; stop same-model attribution, not product observation.', reopen_condition='Independent upstream attestation becomes available.', refs=[dict(source=0,pointer='/note')])]
        self.sync()

    def test_w_nonofficial_ui_product_eligible(self):
        self.valid()
        self.assertEqual(f.reasons(self.e,self.config), [])

    def test_w_wrong_product(self):
        self.e['product']='codex';self.e['identity']['value']['product']='codex';self.sync()
        with self.assertRaises(f.Invalid):self.valid()

    def test_w_cannot_mix_into_a(self):
        self.e['group']='A_same_model';self.e['identity']['value']['group']='A_same_model';self.sync()
        with self.assertRaises(f.Invalid):self.valid()

    def test_w_cannot_mix_into_b(self):
        self.e['group']='B_native';self.e['identity']['value']['group']='B_native';self.sync()
        with self.assertRaises(f.Invalid):self.valid()

    def test_w_wrong_ui_label(self):
        self.e['facts']['model']['value']['ui_label']='DeepSeek Flash';self.sync();self.valid()
        self.assertIn('w_ui_selection_not_frozen',f.reasons(self.e,self.config))

    def test_w_wrong_effort(self):
        self.e['facts']['model']['value']['reasoning_effort']='high';self.sync();self.valid()
        self.assertIn('w_ui_selection_not_frozen',f.reasons(self.e,self.config))

    def test_w_backend_claim_not_allowed(self):
        self.e['facts']['model']['value']['backend_model']='deepseek-v4.1-flash';self.sync();self.valid()
        self.assertIn('w_ui_selection_not_frozen',f.reasons(self.e,self.config))

    def test_w_missing_uncertainty_blocks(self):
        self.e['issues']=[];self.sync();self.valid()
        self.assertIn('w_backend_uncertainty_not_disclosed',f.reasons(self.e,self.config))

    def test_w_scope_cannot_hide_contamination(self):
        self.e['gates']['contamination_free']['value']=False;self.sync();self.valid()
        self.assertIn('gate:contamination_free',f.reasons(self.e,self.config))

    def test_w_scope_cannot_hide_other_unknown(self):
        self.e['facts']['product_version']=f.fact()
        self.e['issues'].append(dict(id='missing-version',unknown_fields=['facts.product_version'],knowledge_status='unknown', investigation_status='stopped',confound_status='not_excluded', impact='missing product version blocks admission',next_step='obtain original receipt',stop_condition='no receipt',reopen_condition='original receipt',refs=[dict(source=0,pointer='/note')]))
        self.sync();self.valid()
        self.assertIn('unknown:product_version',f.reasons(self.e,self.config))
        self.assertIn('confounds_not_excluded',f.reasons(self.e,self.config))

    def test_w_no_generic_scope_waiver(self):
        self.e['issues'][0]['id']='contamination';self.sync()
        with self.assertRaises(f.Invalid):self.valid()

    def test_w_no_hidden_unknown_field_waiver(self):
        self.e['issues'][0]['unknown_fields']=['gates.contamination_free'];self.sync()
        with self.assertRaises(f.Invalid):self.valid()

    def test_w_no_claim_confound_excluded(self):
        self.e['issues'][0]['confound_status']='excluded';self.sync()
        with self.assertRaises(f.Invalid):self.valid()

    def test_w_issue_without_scope_is_not_exception(self):
        del self.e['issues'][0]['attribution_scope'];self.sync();self.valid()
        self.assertIn('confounds_not_excluded',f.reasons(self.e,self.config))

    def test_w_absolute_path_escape(self):
        with self.assertRaises(f.Invalid):f.public_path(self.root,'/etc/passwd')

    def test_w_symlink_escape(self):
        (self.root/'escape').symlink_to(self.root.parent,target_is_directory=True)
        with self.assertRaises(f.Invalid):f.public_path(self.root,'escape/foreign.json')

    def test_w_source_remapping_forbidden(self):
        with self.assertRaises(f.Invalid):f.build(self.root,source_map={'proof.json':'other.json'})

    def test_w_output_scope_restricted(self):
        with self.assertRaises(f.Invalid):f.save_outputs(self.root,{},'5-评测报告/other')

    def test_plan_exact_five(self):
        registrations=[dict(event_id='r20261031-wb-formal:workbuddy:'+case,plan_id=f.W_PLAN_ID,slot_id='workbuddy|'+case,order=1,kind='first',parent_id=None,reason='fixed_first',registered_at=self._t(30)) for case in f.CASES]
        f.validate_w_plan({'registrations':registrations})
        with self.assertRaises(f.Invalid):f.validate_w_plan({'registrations':registrations[:-1]})
        duplicate=copy.deepcopy(registrations);duplicate[-1]=duplicate[0]
        with self.assertRaises(f.Invalid):f.validate_w_plan({'registrations':duplicate})
        wrong=copy.deepcopy(registrations);wrong[0]['slot_id']='codex|'+f.CASES[0]
        with self.assertRaises(f.Invalid):f.validate_w_plan({'registrations':wrong})

    # Inherited A-positive / A-route tests deliberately use A fixture only.
    def test_same_model_wrong_upstream_route(self):
        self.e['issues']=[];self.e.update(group='A_same_model',product='workbuddy')
        self.e['identity']['value']['group']='A_same_model';self.sync();self.valid()
        self.assertIn('official_upstream_route_not_proven',f.reasons(self.e,self.config))

    def test_research_variant_never_official(self):
        self.e['experiment']=True;self.e['identity']['value']['experiment']=True;self.sync();self.valid()
        self.assertIn('research_variant_not_official_product',f.reasons(self.e,self.config))

    def test_mixed_product_group(self):
        self.test_w_wrong_product()


if __name__=='__main__':unittest.main(verbosity=2)
