"""Regression coverage for `.ustats @Member !!` argument parsing."""

import inspect

from cogs.activitystats import ActivityStats


def test_ustats_accepts_trailing_command_text():
    callback = ActivityStats.ustats.callback
    signature = inspect.signature(callback)
    trailing = signature.parameters["trailing"]
    assert trailing.kind is inspect.Parameter.KEYWORD_ONLY
    assert trailing.default == ""

    # The command parser can now consume harmless trailing text instead of
    # raising TooManyArguments before the callback is reached.
    assert "member" in signature.parameters


if __name__ == "__main__":
    test_ustats_accepts_trailing_command_text()
    print("ustats regression passed: `.ustats @Dharam !!` has a trailing-text slot")
