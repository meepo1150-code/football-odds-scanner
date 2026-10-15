import unittest
from unittest.mock import patch
from research.historical_backfill.actions_pilot import probe
from research.historical_backfill.actions_pilot import context_gate, verify_isolation, BRANCH
from research.historical_backfill.isolated_runner import StopPilot

class ActionsSafetyTests(unittest.TestCase):
 def test_only_exact_branch_manual_environment(self):
  valid=dict(GITHUB_REF=BRANCH,GITHUB_EVENT_NAME='workflow_dispatch',PILOT_ENVIRONMENT='historical-research')
  context_gate(valid)
  for key,value in [('GITHUB_REF','refs/heads/main'),('GITHUB_REF',BRANCH.replace('heads','tags')),('GITHUB_EVENT_NAME','schedule'),('GITHUB_EVENT_NAME','pull_request'),('PILOT_ENVIRONMENT','production')]:
   with self.subTest(key=key,value=value),self.assertRaises(StopPilot):context_gate({**valid,key:value})
 def test_shared_subscription_rejected_even_if_key_name_differs(self):
  with self.assertRaises(StopPilot):verify_isolation({'subscription_fingerprint':'same'},{'subscription_fingerprint':'same'})
  verify_isolation({'subscription_fingerprint':'research'},{'subscription_fingerprint':'production'})

class ProbePacingTests(unittest.TestCase):
 def test_account_probe_waits_before_sending_and_does_not_retry_429(self):
  with patch('research.historical_backfill.actions_pilot.time.sleep') as wait, patch('research.historical_backfill.actions_pilot.HttpClient') as client:
   client.return_value.return_value=(429,{},b'')
   with self.assertRaisesRegex(StopPilot,'ACCOUNT_HTTP_429'):probe('test-only-key',set())
   wait.assert_called_once_with(1.2)
   client.return_value.assert_called_once_with('/account',{})

if __name__=='__main__':unittest.main()
