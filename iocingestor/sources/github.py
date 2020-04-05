import datetime
from typing import List, Optional, Tuple, Type

import requests

from iocingestor.artifacts import Artifact, Task
from iocingestor.sources import Source

SEARCH_URL = "https://api.github.com/search/repositories"


class Plugin(Source):
    """Github Source Plugin"""

    def __init__(self, name: str, search: str, username: str = "", token: str = ""):
        self.name = name
        self.search = search
        self.auth: Optional[tuple] = None

        if username and token:
            self.auth = (username, token)

    def _repository_search(self, params: dict):
        """Returns a list of repository results."""
        # Iterates through pages of results from query.
        response = requests.get(SEARCH_URL, params=params, auth=self.auth)

        repo_list = []
        while True:
            for repo in response.json().get("items", []):
                repo_list.append(repo)

            if not response.links.get("next"):
                break

            response = requests.get(response.links.get("next")["url"], auth=self.auth)

        return repo_list

    def run(self, saved_state: str) -> Tuple[str, List[Type[Artifact]]]:
        """Returns a list of artifacts and the saved state"""
        # If no saved_state, search max 1 day ago.
        if not saved_state:
            saved_state = (
                datetime.datetime.utcnow() - datetime.timedelta(days=10)
            ).isoformat()[:-7] + "Z"

        params = {
            "q": "{search} created:>={timestamp}".format(
                search=self.search, timestamp=saved_state
            ),
            "per_page": "100",
        }

        saved_state = datetime.datetime.utcnow().isoformat()[:-7] + "Z"
        repo_list = self._repository_search(params)

        artifact_list = []
        for repo in repo_list:
            title = "Manual Task: GitHub {u}".format(u=repo["full_name"])
            description = "URL: {u}\nTask autogenerated by iocingestor from source: {s}"
            description = description.format(s=self.name, u=repo["html_url"])
            artifact = Task(
                title,
                self.name,
                reference_link=repo["html_url"],
                reference_text=description,
            )

            artifact_list.append(artifact)

        return saved_state, artifact_list