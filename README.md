# gentoo-reminders

Writes a monthly reminder email for each Gentoo package maintainer,
listing:

- the commits to their packages in the previous month

Maintainers with nothing to report get no email. The emails are written
as `.eml` files and are not sent.

## Requirements

- Python 3.11 or later
- a checkout of gentoo.git

## Usage

    pip install .
    cp config.example.toml config.toml
    gentoo-reminders --config config.toml --dry-run --maintainer larry@gentoo.org

`--dry-run` prints the email instead of writing it to `output_dir`.
Without `--maintainer`, every maintainer in the repository is processed.
The previous month is the one before the current month in UTC, so run it
early on the first of each month.

The checkout is updated with `git pull --ff-only` first, unless
`--no-pull` is given.

To send what was written:

    for eml in ~/.local/share/gentoo-reminders/outbox/*.eml; do
        sendmail -t < "$eml" && rm "$eml"
    done

## Tests

    pip install '.[test]'
    pytest

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
