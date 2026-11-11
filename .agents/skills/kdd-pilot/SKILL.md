---
name: kdd-pilot
description: Validate this project's pilot contract with its pinned KDD validator.
---

From the consumer repository root, run `python .kdd/validate.py` with Python 3.11.
Report the exit code and the exact `KDD_PILOT` line produced by the command.
Use the launcher for every run so its lock determines the validator commit.
