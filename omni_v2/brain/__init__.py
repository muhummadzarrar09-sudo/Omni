"""
OMNI BRAIN package (Jarvis Brain, Phase 9).

Holds the persistent "mind of itself" subsystems:
  - identity.py : IdentityCore (sense of self) + UserModel (memory of the user)
  - goals.py    : GoalStack (persistent goal stack: decompose / progress / replan)
  - metacog.py  : Metacog (thinking about its own thinking -> evaluator feedback loop)

These are architecture-only (no model required) so they're fully testable
offline and can be layered in before any bigger model.
"""
