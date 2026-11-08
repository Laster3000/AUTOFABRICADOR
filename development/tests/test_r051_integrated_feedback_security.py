"""R051 original deterministic regression of security guard and feedback."""
from __future__ import annotations
import json
from unittest import TestCase
from autofab import repo_graph,repo_factory


class R051SecurityFeedbackTests(TestCase):
    def test_node_process_execution_and_properties_rejected(self):
        bad=[
            "process.exit(1)",
            "process.env.PATH",
            "process['exit'](1)",
            "process?.exit(1)",
            "globalThis.process.exit(1)",
            "globalThis['process'].exit(1)",
            'globalThis["process"].env',
            "eval('2')",
            "fetch('https://localhost')",
            "require('fs')",
            "import('fs')",
        ]
        for src in bad:
            with self.subTest(source=src):
                with self.assertRaisesRegex(ValueError,"FORBIDDEN|UNSUPPORTED"):
                    repo_graph._static_source_guard({
                        "src/index.ts":"export function example(){ "+src+"; return 42; } // independent regression\n"})

    def test_no_false_positive_for_pure_user_logic(self):
        safe=[
            "export function myprocess(x){ return x+1; }",
            "export function processText(x){ return x.trim(); }",
            "export function add(a,b){ return a+b; }",
        ]
        for source in safe:
            with self.subTest(source=source):
                repo_graph._static_source_guard({"src/index.ts":source+"\n"})

    def test_actionable_feedback_binds_original_owner_args(self):
        spec={"acceptance":[
            {"args":["127.0.0.1"],"expected":True},
            {"args":["01.2.3.4"],"expected":False},
            {"args":["1.2.3.4"],"expected":True},
            {"args":["0.00.0.0"],"expected":False}
        ]}
        result={"status":"FAILED_OWNER_WASI",
            "originalOwnerResult":{"testResult":{"failed":[
                {"i":1,"expected":False,"got":True},
                {"i":3,"expected":False,"got":True}]}}}
        original=json.dumps(spec,sort_keys=True)
        feedback=repo_factory._feedback(result,spec)
        self.assertIn("01.2.3.4",feedback)
        self.assertIn("0.00.0.0",feedback)
        self.assertIn("GENERAL RULE",feedback)
        self.assertIn("false",feedback.lower())
        self.assertEqual(json.dumps(spec,sort_keys=True),original)
        self.assertIn("WASI",repo_factory._feedback(result))

    def test_out_of_range_owner_failure_index_discarded(self):
        source={"acceptance":[{"args":[1],"expected":1}]}
        result={"status":"FAILED_OWNER_WASI",
           "originalOwnerResult":{"testResult":{"failed":[{"i":12345,"got":0}]}}}
        feedback=repo_factory._feedback(result,source)
        self.assertIn("GENERAL RULE",feedback)
        self.assertIn("12345",feedback)
