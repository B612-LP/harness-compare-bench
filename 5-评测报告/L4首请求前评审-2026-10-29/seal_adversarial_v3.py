#!/usr/bin/env python3
"""Eight fixed synthetic source-binding checks; no real payload or model executes."""
import argparse
import datetime as dt
import json
from pathlib import Path
from seal_adversarial_v2 import Harness, sha


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    cases = []
    names = ('positive', 'empty_files', 'omitted_clarification', 'same_bytes_source_symlink',
             'new_unsealed_py', 'runtime_symlink_directory', 'extensionless_helper', 'generated_workspace_not_source')
    for attack in names:
        h = Harness(a.source.resolve())
        expected_reject = attack not in ('positive', 'generated_workspace_not_source')
        try:
            if attack == 'runtime_symlink_directory':
                external = h.base / 'external-package'
                external.mkdir()
                (external / 'payload.py').write_text('SYNTHETIC_CONSTANT=1\n')
                (h.runner.parent / 'helpers').symlink_to(external, target_is_directory=True)
                h.runner.write_text('from helpers import payload\n# Never executed\n')
            h.manifest()
            doc = json.loads(h.mod.MANIFEST.read_text())
            if attack == 'empty_files':
                doc['files'] = {}
            elif attack == 'omitted_clarification':
                del doc['files']['1-plan/loop4/CLARIFICATION-L4-1.md']
            if attack in ('empty_files', 'omitted_clarification'):
                h.mod.MANIFEST.write_text(json.dumps(doc) + '\n')
            seal = h.commit('synthetic E')
            if attack == 'same_bytes_source_symlink':
                target = h.base / 'outside-same-byte.py'
                target.write_bytes(h.runner.read_bytes())
                assert h.runner.resolve() == h.root / h.mod.REQUIRED_RUNTIME[0]
                h.runner.unlink()
                h.runner.symlink_to(target)
            elif attack == 'new_unsealed_py':
                (h.runner.parent / 'new-unsealed.py').write_text('# synthetic\n')
            elif attack == 'extensionless_helper':
                (h.runner.parent / 'unsealed-helper').write_text('# synthetic extensionless code/config\n')
            elif attack == 'generated_workspace_not_source':
                artifact = h.root / '3-表现现场/l4-20261029-cli/codex/runs/synthetic/workspace/generated.py'
                artifact.parent.mkdir(parents=True)
                artifact.write_text('# synthetic assessed artifact, NOT runner infrastructure\n')
            observed = h.bind(seal)
        except Exception as exc:
            observed = {'rejected': True, 'exception': type(exc).__name__, 'error': str(exc), 'stage': 'manifest_or_setup'}
        finally:
            h.close()
        cases.append({'id': attack, 'expected_rejected': expected_reject,
                      'pass': observed['rejected'] == expected_reject,
                      'observed': observed, 'payload_executed': False})
    result = {'category': 'self_test', 'scope': 'Independent synthetic git only, zero APIs, no payload execution',
              'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
              'source_sha256': sha(a.source.resolve()), 'reviewer_script_sha256': sha(Path(__file__)),
              'harness_sha256': sha(Path(__file__).with_name('seal_adversarial_v2.py')),
              'live_doc_drift': [], 'checks': cases, 'passed': all(x['pass'] for x in cases)}
    with a.out.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'passed': result['passed'], 'checks': len(cases), 'failed': [x['id'] for x in cases if not x['pass']], 'out': str(a.out)}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
