#!/usr/bin/env python3
"""Checker-owned completion accounting, not a sandbox for hostile Python.

Run with -I -S. Import trusted stdlib and install accounting before candidate
imports. Emit a separate receipt only after suite.run returns normally.
A same-UID adversary can still introspect/patch this process or access host files;
use an OS sandbox for untrusted submissions (see spec).
"""
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path

PROTOCOL = 'exercism-completion-v1'
_dump = json.dumps
_open = io.open


class AccountingResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.started_ids = []
        self.stopped_ids = []
        self.success_ids = []

    def startTest(self, test):
        self.started_ids.append(test.id())
        super().startTest(test)

    def stopTest(self, test):
        self.stopped_ids.append(test.id())
        super().stopTest(test)

    def addSuccess(self, test):
        self.success_ids.append(test.id())
        super().addSuccess(test)


def main():
    exdir, receipt = Path(sys.argv[1]), Path(sys.argv[2])
    ex = exdir.name
    # Under -I, the candidate directory cannot shadow unittest/json/site imports.
    loader = unittest.TestLoader()
    result = AccountingResult()
    sys.path.insert(0, str(exdir))
    spec = importlib.util.spec_from_file_location(ex + '_test', exdir / (ex + '_test.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite = loader.loadTestsFromModule(module)
    discovered = suite.countTestCases()
    suite.run(result)
    payload = {
        'protocol': PROTOCOL, 'complete': True,
        'discovered': discovered, 'tests_run': result.testsRun,
        'started_ids': result.started_ids, 'stopped_ids': result.stopped_ids,
        'success_ids': result.success_ids,
        'failures': len(result.failures), 'errors': len(result.errors),
        'skipped': len(result.skipped), 'expected_failures': len(result.expectedFailures),
        'unexpected_successes': len(result.unexpectedSuccesses),
    }
    with _open(receipt, 'w', encoding='utf-8') as handle:
        handle.write(_dump(payload))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
