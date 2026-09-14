"""Regression coverage for `.ustats @Member !!` argument parsing."""

import inspect
import sys
from pathlib import Path

# Running a test file directly sets sys.path[0] to ``tests/``. Add the repo
# root so the same command used by CI can import the bot package.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cogs.activitystats import ActivityStats


def test_ustats_accepts_trailing_command_text():
    callback = ActivityStats.ustats.callback
    signature = inspect.signature(callback)
    trailing = signature.parameters["trailing"]
    assert trailing.kind is inspect.Parameter.KEYWORD_ONLY
    assert trailing.default == ""
    assert "member" in signature.parameters

    # This is the parser-level contract for the exact failing input:
    # ``.ustats @Dharam !!`` must leave ``!!`` in the keyword-only remainder
    # instead of raising TooManyArguments before the callback is reached.
    command = ActivityStats.ustats
    clean_params = command.clean_params
    assert "member" in clean_params
    assert "trailing" in clean_params
    assert clean_params["trailing"].kind is inspect.Parameter.KEYWORD_ONLY


if __name__ == "__main__":
    test_ustats_accepts_trailing_command_text()
    print("ustats regression passed: `.ustats @Dharam !!` accepts trailing text")
