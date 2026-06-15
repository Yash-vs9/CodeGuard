from scratch_tools import _is_blocked

commands = [
    "npm run dev",
    "python manage.py runserver",
    "rg something",
    "rg --glob '*.py' something",
    "ls -R",
    "ls -r",
    "grep -r",
    "cat bigfile.txt",
    "cat",
    "echo .next",
    "ls node_modules",
]

for cmd in commands:
    print(f"[{cmd}] -> Blocked: {_is_blocked(cmd)}")
