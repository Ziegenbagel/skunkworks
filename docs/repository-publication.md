# Publishing the Repository Safely

The current branch removes live databases and raw sector snapshots from the
public tree, but deletion commits do not erase earlier Git objects. Before
changing repository visibility to public, an owner must inspect and, if needed,
rewrite all branches and tags containing private game data.

## Required pre-publication process

1. Keep an offline backup of the original private repository.
2. Freeze pushes and coordinate with every collaborator.
3. Use a dedicated history-rewriting tool such as `git filter-repo` to remove
   the known runtime database and snapshot paths from every ref.
4. Search the rewritten history for credentials, database files, raw snapshots,
   probe/player names, messages, and other account-specific values.
5. Force-push rewritten branches and tags only after review.
6. Delete or rotate any credential ever committed, even if history was rewritten.
7. Require collaborators to discard old clones rather than merge their histories
   back into the sanitized repository.

History rewriting is intentionally not automated by Skunkworks because it is a
destructive repository-owner operation. GitHub's sensitive-data removal guidance
and the chosen hosting plan should be reviewed immediately before performing it.

## Clean release staging

Build packages from a fresh checkout of the approved tag, never from the working
development directory. Run:

```bash
python -m tools.release_readiness
python -m tools.audit_release_tree .
```

Run the tree audit again against every unpacked candidate artifact before
signing. The build workflow must use an allowlist and must never package ignored
files merely because they exist on a developer machine.
