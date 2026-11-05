# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import json
import logging
import os
import re

from ..util import run
from .pull_requests import PullRequest, PullRequestsCollector

log = logging.getLogger(__name__)

# GitHub often answers with a 502 when asked for many more of these at once.
# It lists at most the first 100 files of each pull request.
QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: OPEN, first: 50, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes { number title url files(first: 100) { nodes { path } } }
    }
  }
}
"""


async def request(*args: str, env: dict[str, str] | None) -> str:
    # GitHub sometimes answers with a 502, or a rate limit that asks to wait
    # a few minutes.
    for delay in (10, 30, 300):
        try:
            return await run(*args, env=env)
        except RuntimeError as e:
            if not re.search(r"\bHTTP 5\d\d\b|rate limit", str(e)):
                raise
            log.warning("%s, retrying in %ds", e, delay)
            await asyncio.sleep(delay)
    return await run(*args, env=env)


class GitHubPRsCollector(PullRequestsCollector):
    title = "Open GitHub Pull Requests"
    forge = "GitHub"

    async def fetch(self) -> list[PullRequest]:
        owner, name = self.config.github_repo.split("/")
        args = ("gh", "api", "graphql", "-f", f"query={QUERY}",
                "-f", f"owner={owner}", "-f", f"name={name}")
        token = self.config.github_token
        env = {**os.environ, "GH_TOKEN": token} if token else None

        prs = []
        after = ()
        while True:
            out = await request(*args, *after, env=env)
            page = json.loads(out)["data"]["repository"]["pullRequests"]
            prs += [
                PullRequest(pr["number"], pr["title"], pr["url"],
                            [f["path"] for f in pr["files"]["nodes"]])
                for pr in page["nodes"]
            ]
            if not page["pageInfo"]["hasNextPage"]:
                return prs
            after = ("-f", f"cursor={page['pageInfo']['endCursor']}")
