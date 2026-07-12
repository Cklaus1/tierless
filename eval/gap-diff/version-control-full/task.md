# Version control task

You've finished a work session and have a pile of uncommitted changes in your working tree. Here is
`git status` and a summary of what changed:

```
$ git status --short
 M src/auth/session.py          # renamed validate_token() -> verify_token(); also fixed a real
                                #   bug where expired tokens were accepted (the reason you started)
 M src/auth/middleware.py       # calls the renamed function; also you reformatted the whole file
                                #   (your editor ran black on save)
 M src/api/login.py             # calls the renamed function
 M src/api/refresh.py           # STILL calls validate_token() — you missed this one
 M tests/test_session.py        # updated for the rename + a new test for the expiry bug
 M docs/auth.md                 # mentions validate_token() in a code example — not updated
 M requirements.txt             # bumped cryptography 41.0 -> 42.0 while debugging (unrelated)
?? scratch/debug_dump.json      # a 2MB file you created while investigating
```

You need to turn this into commits and get it reviewed/merged. Walk through exactly how you'd do it:
what commits you'd make and in what order, what goes in each, what you'd check before committing,
and anything about this situation that's a trap. Be specific and thorough.
