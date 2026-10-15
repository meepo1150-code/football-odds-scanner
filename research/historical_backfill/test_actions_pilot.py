import unittest
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

if __name__=='__main__':unittest.main()
