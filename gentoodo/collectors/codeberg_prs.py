# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import json

from ..util import fetch_with_headers
from .pull_requests import PullRequest, PullRequestsCollector

URL = "https://codeberg.org"

# Forgejo's largest page size by default
PAGE_SIZE = 50

# Pull requests whose files are fetched at once
CONCURRENCY = 4


def next_link(header: str | None) -> str | None:
    """Return the URL with rel="next" in a Link header, if any."""
    for link in (header or "").split(","):
        url, *params = (part.strip() for part in link.split(";"))
        if any(param.replace('"', "") == "rel=next" for param in params):
            return url.strip("<>")
    return None


async def fetch_pages(url: str) -> list:
    """GET each page of a paginated Forgejo API list."""
    results = []
    while url:
        data, headers = await asyncio.to_thread(fetch_with_headers, url)
        results += json.loads(data)
        url = next_link(headers.get("Link"))
    return results


class CodebergPRsCollector(PullRequestsCollector):
    title = "Open Codeberg Pull Requests"
    forge = "Codeberg"

    async def fetch(self) -> list[PullRequest]:
        api = f"{URL}/api/v1/repos/{self.config.codeberg_repo}/pulls"
        query = f"limit={PAGE_SIZE}"

        # https://codeberg.org/api/swagger#/repository/repoListPullRequests
        # A pull request that could not be retrieved is null in the list.
        prs = [pr for pr in await fetch_pages(f"{api}?state=open&{query}") if pr]

        semaphore = asyncio.Semaphore(CONCURRENCY)

        # https://codeberg.org/api/swagger#/repository/repoGetPullRequestFiles
        async def files(pr: dict) -> PullRequest:
            async with semaphore:
                pr_files = await fetch_pages(f"{api}/{pr['number']}/files?{query}")
            return PullRequest(pr["number"], pr["title"], pr["html_url"],
                               [f["filename"] for f in pr_files])

        return await asyncio.gather(*map(files, prs))
