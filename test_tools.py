from scratch_tools import _validate_path, IGNORE_DIRS
from pathlib import Path
import os

try:
    _validate_path(".git/config")
    print("FAILED: Did not block .git")
except ValueError as e:
    print("PASSED: Blocked .git:", e)

try:
    _validate_path("../outside")
    print("FAILED: Did not block outside path")
except ValueError as e:
    print("PASSED: Blocked outside path:", e)

