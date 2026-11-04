# gentoodo

Writes a monthly reminder email for each Gentoo package maintainer,
listing:

- their packages with a newer upstream version, from packages.gentoo.org
  (which gets them from Repology)
- their package versions that are ready for stabilization, from Gentoo's
  CI
- the open GitHub pull requests that touch their packages
- their redundant package versions, from Gentoo's CI
- the commits to their packages in the previous month (for a project,
  split into commits by its members and by others)
- the pkgcheck errors and warnings new in the previous month, from
  Gentoo's CI
- the bugs assigned to them that were filed or closed in the previous
  month, and those still open, from the Gentoo Linux product of
  bugs.gentoo.org

Stabilization and keywording commits and bugs are counted rather than
listed.

Maintainers with nothing to report get no email. The emails are written
as `.eml` files, and sent in a separate step. If GitHub cannot be read,
the emails say so in place of the pull requests.

## Requirements

- Python 3.11 or later
- the [GitHub CLI](https://cli.github.com/), logged in, or a token in the
  file named by `secret_file` in the `[github]` section of the configuration
- a [bugs.gentoo.org API key](https://bugs.gentoo.org/userprefs.cgi?tab=apikey),
  in the file named by `secret_file` in the `[bugzilla]` section of the
  configuration

gentoo.git is cloned into `cache_dir` on the first run and fetched on
each run after. Only the `metadata.xml` files, `.mailmap` and the history
are read, so the clone is a bare partial clone. To use a repository of
your own instead, set `gentoo_repo`. It can be bare, but must have its
history: a shallow clone gives wrong reports. Its `metadata.xml` files
are read as committed in `HEAD`.

## Usage

    pip install .
    cp config.example.toml config.toml
    gentoodo --config config.toml --dry-run --maintainer larry@gentoo.org

`--dry-run` prints the email instead of writing it to `output_dir`.
Without `--maintainer`, every maintainer in the repository is processed.
New QA warnings, commits, and bugs filed and closed are those of the
previous month, the one before the current month in UTC, so run it early
on the first of each month. `--month 2026-10` reports on October 2026
instead, up to now if it is the current month.

Unless `--no-pull` is given, the repository is first updated with
`git fetch`, or with `git pull --ff-only` if it is not bare.
`--collectors` limits the run to some of
`outdated`, `stable_requests`, `github_prs`, `redundant`, `shortlog`,
`qa`, `new_bugs` and `bugs`.

The pkgcheck reports of Gentoo's CI come from
[qa-reports.gentoo.org](https://qa-reports.gentoo.org/), found by date
in the commits of
[gentoo-ci.git](https://anongit.gentoo.org/git/report/gentoo-ci.git),
kept in `cache_dir`. New QA warnings are those in the last report of the
previous month and not in the last report before it, ignoring versions,
line numbers and bracketed lists, and checks with no results in the
earlier report.

To send what was written, with the `sendmail` of the configuration:

    gentoodo --config config.toml --send-outbox

Each email sent is moved to `sent` in `output_dir`. Those that fail stay
behind, to be sent by the next `--send-outbox`. With `--dry-run`, it
lists what it would send. With `--maintainer`, it sends only the emails
to that maintainer, leaving the rest in `output_dir`.

To copy every email to a mailing list, set `cc` in the `[general]`
section of the configuration. The list receives the same emails as
maintainers, including any restricted bugs the Bugzilla API key can see.

## Limitations

- Pull requests are matched on the first 100 files they change.

## Tests

    pip install '.[test]'
    pytest

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
