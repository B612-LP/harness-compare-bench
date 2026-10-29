#!/usr/bin/env python3
"""Synthetic git repositories only; no credentials, model APIs, or benchmark answers."""
import argparse
import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path

SOURCE = Path(__file__).with_name('execution_seal.py')

class SealTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='hcb-l4-seal-test-')
        self.root = Path(self.tmp.name).resolve()
        self.here = self.root/'1-plan'/'loop4'
        self.here.mkdir(parents=True)
        spec = importlib.util.spec_from_file_location('l4seal_under_test', SOURCE)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.mod.ROOT = self.root
        self.mod.HERE = self.here
        self.mod.MANIFEST = self.here/'execution-manifest.json'
        self.mod.BINDING = self.here/'runtime-binding.json'
        self.mod.__file__ = str(self.here/'execution_seal.py')
        self.mod.REQUIRED_EXTERNAL_FILES=tuple(self.root/'external-profile-fixtures'/name for name in ('profile.yml','package.json','AGENTS.md','codex-config.toml','WB-Info.plist','WB-app.asar'))
        self.mod.REQUIRED_EXECUTABLES=()  # isolated fixtures need no actual benchmark products
        for path in self.mod.REQUIRED_EXTERNAL_FILES:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('# external synthetic configuration\n')
        (self.here/'execution_seal.py').write_bytes(SOURCE.read_bytes())
        for name in ('PREREGISTRATION.md','plan.json','contract.json','CLARIFICATION-L4-1.md','test_execution_seal.py'):
            (self.here/name).write_text('{}\n',encoding='utf-8')
        for name in self.mod.REQUIRED_RUNTIME:
            path=self.root/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('# synthetic fixture; never executed\n',encoding='utf-8')
        self.run_git('init','-q')
        self.run_git('config','user.name','Synthetic L4 Test')
        self.run_git('config','user.email','synthetic@example.invalid')
        self.design = self.commit('synthetic design')

    def tearDown(self):
        self.tmp.cleanup()

    def run_git(self,*args):
        return subprocess.run(['git','-C',str(self.root),*args],capture_output=True,check=True).stdout.decode().strip()

    def commit(self,msg):
        # This is an isolated synthetic repository, never the user's repository.
        self.run_git('add','1-plan/loop4','1-评测方案','3-表现现场')
        self.run_git('commit','-qm',msg)
        return self.run_git('rev-parse','HEAD')

    def manifest(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.mod.manifest(argparse.Namespace(design=self.design,file=[],external_file=[]))

    def bind(self,seal):
        with contextlib.redirect_stdout(io.StringIO()):
            self.mod.bind(argparse.Namespace(seal=seal,release=True))

    def test_binding_matches_real_committer_time_and_blobs(self):
        self.manifest()
        seal=self.commit('synthetic execution seal')
        self.bind(seal)
        b=json.loads(self.mod.BINDING.read_text())
        self.assertEqual(b['registered_at'],self.run_git('show','-s','--format=%cI',seal))
        self.assertEqual(b['preregistration_commit'],seal)
        self.assertTrue(b['released_for_model_calls'])

    def test_design_drift_is_rejected(self):
        (self.here/'plan.json').write_text('{"changed":true}\n')
        with self.assertRaisesRegex(ValueError,'Design drift'):
            self.manifest()

    def test_source_drift_after_execution_seal_is_rejected(self):
        self.manifest()
        seal=self.commit('synthetic execution seal')
        (self.here/'execution_seal.py').write_text('# changed\n')
        with self.assertRaisesRegex(ValueError,'Source drift'):
            self.bind(seal)

    def test_uncommitted_manifest_is_rejected(self):
        self.manifest()
        with self.assertRaises(subprocess.CalledProcessError):
            self.bind(self.design)

    def test_manifest_and_binding_refuse_overwrite(self):
        self.manifest()
        before=self.mod.MANIFEST.read_bytes()
        with self.assertRaises(FileExistsError):
            self.manifest()
        self.assertEqual(self.mod.MANIFEST.read_bytes(),before)
        seal=self.commit('synthetic execution seal')
        self.bind(seal)
        binding=self.mod.BINDING.read_bytes()
        with self.assertRaises(FileExistsError):
            self.bind(seal)
        self.assertEqual(self.mod.BINDING.read_bytes(),binding)

    def test_empty_sealed_manifest_is_rejected(self):
        self.manifest()
        doc=json.loads(self.mod.MANIFEST.read_text())
        doc['files']={}
        self.mod.MANIFEST.write_text(json.dumps(doc))
        seal=self.commit('malformed empty manifest')
        with self.assertRaisesRegex(ValueError,'nonempty'):
            self.bind(seal)

    def test_omitted_clarification_is_rejected(self):
        self.manifest()
        doc=json.loads(self.mod.MANIFEST.read_text())
        del doc['files']['1-plan/loop4/CLARIFICATION-L4-1.md']
        self.mod.MANIFEST.write_text(json.dumps(doc))
        seal=self.commit('malformed omitted clarification')
        with self.assertRaisesRegex(ValueError,'missing required'):
            self.bind(seal)

    def test_same_byte_external_symlink_is_rejected(self):
        self.manifest()
        seal=self.commit('synthetic execution seal')
        path=self.here/'contract.json'
        outside=self.root/'same-byte-external-copy'
        outside.write_bytes(path.read_bytes())
        # Synthetic isolated path, resolved and asserted before replacement.
        self.assertEqual(path.resolve(),self.here/'contract.json')
        path.unlink()
        path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError,'symlink'):
            self.bind(seal)

    def test_new_runtime_module_requires_new_manifest(self):
        self.manifest()
        seal=self.commit('synthetic execution seal')
        new=self.root/self.mod.RUNTIME_ROOTS[0]/'unsealed-helper.py'
        new.write_text('# unsealed')
        with self.assertRaisesRegex(ValueError,'missing required'):
            self.bind(seal)

    def test_cli_binary_is_mandatory_external_source(self):
        executable=self.root/'synthetic-cli-binary'
        executable.write_text('# fixture, never executed')
        self.mod.REQUIRED_EXECUTABLES=('fixture-cli',)
        with mock.patch.object(self.mod.shutil,'which',return_value=str(executable)):
            self.manifest()
            doc=json.loads(self.mod.MANIFEST.read_text())
            self.assertIn(str(executable),doc['external_files'])
            del doc['external_files'][str(executable)]
            self.mod.MANIFEST.write_text(json.dumps(doc))
            seal=self.commit('malformed omitted binary')
            with self.assertRaisesRegex(ValueError,'mandatory external'):
                self.bind(seal)

    def test_codex_native_payload_is_pinned_not_just_launcher(self):
        package=self.root/'synthetic-codex-package'
        launcher=package/'bin/codex.js'
        native=package/'node_modules/@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex'
        launcher.parent.mkdir(parents=True)
        launcher.write_text('// fixture launcher, never executed')
        native.parent.mkdir(parents=True)
        native.write_text('# native fixture bytes, never executed')
        self.mod.REQUIRED_EXECUTABLES=('codex',)
        with mock.patch.object(self.mod.shutil,'which',return_value=str(launcher)):
            self.manifest()
            doc=json.loads(self.mod.MANIFEST.read_text())
            self.assertIn(str(native),doc['external_files'])
            del doc['external_files'][str(native)]
            self.mod.MANIFEST.write_text(json.dumps(doc))
            seal=self.commit('malformed omitted native payload')
            with self.assertRaisesRegex(ValueError,'mandatory external'):
                self.bind(seal)

    def test_missing_cli_binary_is_rejected(self):
        self.mod.REQUIRED_EXECUTABLES=('fixture-cli',)
        with mock.patch.object(self.mod.shutil,'which',return_value=None):
            with self.assertRaisesRegex(ValueError,'Missing execution binary'):
                self.manifest()

    def test_empty_external_configuration_manifest_is_rejected(self):
        self.manifest()
        doc=json.loads(self.mod.MANIFEST.read_text())
        doc['external_files']={}
        self.mod.MANIFEST.write_text(json.dumps(doc))
        seal=self.commit('malformed missing external configuration')
        with self.assertRaisesRegex(ValueError,'mandatory external'):
            self.bind(seal)

    def test_external_configuration_drift_is_rejected(self):
        self.manifest()
        seal=self.commit('synthetic execution seal')
        self.mod.REQUIRED_EXTERNAL_FILES[0].write_text('# changed external config')
        with self.assertRaisesRegex(ValueError,'External source drift'):
            self.bind(seal)

    def test_runtime_symlink_directory_is_rejected(self):
        self.manifest()
        seal=self.commit('synthetic execution seal')
        outside=self.root/'external-import-directory'
        outside.mkdir()
        (outside/'payload.py').write_text('# never executed')
        link=self.root/self.mod.RUNTIME_ROOTS[0]/'helpers'
        link.symlink_to(outside,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlink'):
            self.bind(seal)

    def test_extensionless_runtime_file_requires_manifest(self):
        self.manifest()
        seal=self.commit('synthetic execution seal')
        path=self.root/self.mod.RUNTIME_ROOTS[0]/'extensionless-loader-input'
        path.write_text('# never executed')
        with self.assertRaisesRegex(ValueError,'missing required'):
            self.bind(seal)

    def test_generated_solution_artifacts_are_not_runtime_sources(self):
        self.manifest()
        seal=self.commit('synthetic execution seal')
        artifact=self.root/'3-表现现场/l4-20261029-cli/codex/runs/slot/workspace/program.py'
        artifact.parent.mkdir(parents=True)
        artifact.write_text('# generated artifact, not execution infrastructure\n')
        self.bind(seal)
        self.assertTrue(self.mod.BINDING.is_file())

    def test_dangling_symlink_refuses_create(self):
        target=self.here/'missing-target'
        path=self.here/'new.json'
        path.symlink_to(target)
        with self.assertRaises(FileExistsError):
            self.mod.create(path,{'not':'written'})
        self.assertFalse(target.exists())

if __name__=='__main__':
    unittest.main(verbosity=2)
