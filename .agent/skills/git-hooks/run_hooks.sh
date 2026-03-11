#!/bin/bash
# Manual hook runner for agents

if [ -f ".git/hooks/pre-commit" ]; then
    bash .git/hooks/pre-commit
else
    bash .agent/skills/git-hooks/install.sh
    bash .git/hooks/pre-commit
fi
