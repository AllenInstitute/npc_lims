# Contributing

Contributions are welcome, and they are greatly appreciated!
Every little bit helps, and credit will always be given.

## Environment setup

Nothing easier!

Fork and clone the repository:

```bash
git clone https://github.com/AllenInstitute/npc_lims
cd npc_lims
```

We use [pdm](https://pdm.fming.dev) to manage the project and dependencies, install PDM if it isn't done yet, then:

```bash
pdm install
```

You now have the dependencies installed.

You can run the tests with `pdm run test [ARGS...]`.

## Development

As usual:

1. create a new branch: `git checkout -b feature-or-bugfix-name`
1. edit the code and/or the documentation

If you updated the documentation or the project dependencies:

1. run `pdm run doc`
1. go to http://localhost:8000 and check that everything looks good

**Before committing:**

1. Make sure you submit a news entry under `news/` directory with the name pattern `<issue_or_pr_num>.<type>.md` where `<type>` should be one of:
   1. `bugfix` for bug fixes
   1. `feature` for features and improvements
   1. `doc` for documentation improvements
   1. `remove` for deprecations and removals
   1. `dep ` for dependencies updates
   1. `misc` for miscellany tasks

1. Install [pre-commit](https://pre-commit.com/) and hooks:
   ```bash
   pre-commit install
   ```
1. Then linter task will be run each time when you commit something. Or you can run it manually:
   ```bash
   pdm run lint
   ```

If you are unsure about how to fix or ignore a warning,
just let the continuous integration fail,
and we will help you during review.

Don't bother updating the changelog, we will take care of this.

## Pull requests guidelines

Link to any related issue in the Pull Request message.

During review, we recommend using fixups:

```bash
# SHA is the SHA of the commit you want to fix
git commit --fixup=SHA
```

Once all the changes are approved, you can squash your commits:

```bash
git rebase -i --autosquash master
```

And force-push:

```bash
git push -f
```

If this seems all too complicated, you can push or force-push each new commit,
and we will squash them ourselves if needed, before merging.
