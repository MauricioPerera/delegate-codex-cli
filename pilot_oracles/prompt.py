"""Run the existing prompt regression case through KDD's file-based runner."""

import unittest

from tests import test_skill


class PromptOracle(test_skill.SkillTests):
    """Attribute the existing case to the sealed adapter file."""


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        PromptOracle("test_kdd_prefix_is_deterministic_and_goal_is_last"),
    ])
