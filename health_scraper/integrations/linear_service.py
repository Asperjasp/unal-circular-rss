"""
Linear Integration Service
===========================
Integrates with Linear's GraphQL API for project management.
Supports creating/tracking issues for both development and commercial tasks.

Linear API docs: https://developers.linear.app/docs/graphql/working-with-the-graphql-api

Setup:
1. Go to Linear Settings → API → Personal API Keys
2. Create a new key and add it to your .env as LINEAR_API_KEY
3. Get your team ID from Linear Settings → Teams
"""

import logging
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"


class LinearPriority(int, Enum):
    """Linear issue priority levels"""
    NO_PRIORITY = 0
    URGENT = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class LinearService:
    """Service for interacting with Linear's GraphQL API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
        }
        self._teams_cache: Optional[List[Dict]] = None
        self._labels_cache: Optional[Dict[str, str]] = None

    async def _execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a GraphQL query against Linear API"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                LINEAR_GRAPHQL_URL,
                json=payload,
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                error_msg = "; ".join(e.get("message", "") for e in data["errors"])
                raise Exception(f"Linear API error: {error_msg}")

            return data.get("data", {})

    # ── Teams & Labels ────────────────────────────────────────────────

    async def get_teams(self) -> List[Dict[str, Any]]:
        """Get all teams in the workspace"""
        if self._teams_cache:
            return self._teams_cache

        query = """
        query {
            teams {
                nodes {
                    id
                    name
                    key
                    states {
                        nodes { id name type }
                    }
                }
            }
        }
        """
        result = await self._execute_query(query)
        self._teams_cache = result.get("teams", {}).get("nodes", [])
        return self._teams_cache

    async def get_labels(self, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all issue labels"""
        query = """
        query($teamId: String) {
            issueLabels(filter: { team: { id: { eq: $teamId } } }) {
                nodes { id name color }
            }
        }
        """
        variables = {"teamId": team_id} if team_id else {}
        result = await self._execute_query(query, variables)
        return result.get("issueLabels", {}).get("nodes", [])

    async def get_or_create_label(self, team_id: str, name: str, color: str = "#6B7280") -> str:
        """Get existing label or create a new one. Returns label ID"""
        labels = await self.get_labels(team_id)
        for label in labels:
            if label["name"].lower() == name.lower():
                return label["id"]

        # Create new label
        mutation = """
        mutation($input: IssueLabelCreateInput!) {
            issueLabelCreate(input: $input) {
                success
                issueLabel { id name }
            }
        }
        """
        result = await self._execute_query(mutation, {
            "input": {"name": name, "color": color, "teamId": team_id}
        })
        return result["issueLabelCreate"]["issueLabel"]["id"]

    # ── Issues ────────────────────────────────────────────────────────

    async def create_issue(
        self,
        team_id: str,
        title: str,
        description: Optional[str] = None,
        priority: LinearPriority = LinearPriority.MEDIUM,
        label_ids: Optional[List[str]] = None,
        assignee_id: Optional[str] = None,
        due_date: Optional[str] = None,  # ISO format: "2026-03-15"
    ) -> Dict[str, Any]:
        """
        Create a new issue in Linear.

        Returns dict with issue id, identifier (e.g. 'ENG-42'), url.
        """
        mutation = """
        mutation($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                    url
                    state { name }
                    createdAt
                }
            }
        }
        """
        input_data: Dict[str, Any] = {
            "teamId": team_id,
            "title": title,
            "priority": priority.value,
        }
        if description:
            input_data["description"] = description
        if label_ids:
            input_data["labelIds"] = label_ids
        if assignee_id:
            input_data["assigneeId"] = assignee_id
        if due_date:
            input_data["dueDate"] = due_date

        result = await self._execute_query(mutation, {"input": input_data})
        issue = result["issueCreate"]["issue"]
        logger.info(f"Created Linear issue: {issue['identifier']} - {issue['title']}")
        return issue

    async def create_development_task(
        self,
        team_id: str,
        title: str,
        description: str,
        priority: LinearPriority = LinearPriority.MEDIUM,
        assignee_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Shortcut to create a development-category issue with 'Desarrollo' label"""
        label_id = await self.get_or_create_label(team_id, "Desarrollo", "#3B82F6")
        return await self.create_issue(
            team_id=team_id,
            title=title,
            description=description,
            priority=priority,
            label_ids=[label_id],
            assignee_id=assignee_id,
        )

    async def create_commercial_task(
        self,
        team_id: str,
        title: str,
        description: str,
        company_name: Optional[str] = None,
        priority: LinearPriority = LinearPriority.MEDIUM,
        assignee_id: Optional[str] = None,
        due_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Shortcut to create a commercial-category issue with 'Comercial' label"""
        label_id = await self.get_or_create_label(team_id, "Comercial", "#F59E0B")
        desc = description
        if company_name:
            desc = f"**Empresa:** {company_name}\n\n{description}"
        return await self.create_issue(
            team_id=team_id,
            title=title,
            description=desc,
            priority=priority,
            label_ids=[label_id],
            assignee_id=assignee_id,
            due_date=due_date,
        )

    async def get_issues(
        self,
        team_id: Optional[str] = None,
        state_name: Optional[str] = None,
        label_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get issues with optional filters"""
        filters = []
        if team_id:
            filters.append(f'team: {{ id: {{ eq: "{team_id}" }} }}')
        if state_name:
            filters.append(f'state: {{ name: {{ eq: "{state_name}" }} }}')
        if label_name:
            filters.append(f'labels: {{ name: {{ eq: "{label_name}" }} }}')

        filter_str = ", ".join(filters)
        filter_clause = f"filter: {{ {filter_str} }}," if filters else ""

        query = f"""
        query {{
            issues({filter_clause} first: {limit}, orderBy: updatedAt) {{
                nodes {{
                    id
                    identifier
                    title
                    description
                    priority
                    url
                    state {{ name type }}
                    labels {{ nodes {{ name color }} }}
                    assignee {{ name email }}
                    dueDate
                    createdAt
                    updatedAt
                }}
            }}
        }}
        """
        result = await self._execute_query(query)
        return result.get("issues", {}).get("nodes", [])

    async def update_issue(
        self,
        issue_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        state_id: Optional[str] = None,
        priority: Optional[LinearPriority] = None,
    ) -> Dict[str, Any]:
        """Update an existing issue"""
        mutation = """
        mutation($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
                issue { id identifier title state { name } }
            }
        }
        """
        input_data: Dict[str, Any] = {}
        if title:
            input_data["title"] = title
        if description:
            input_data["description"] = description
        if state_id:
            input_data["stateId"] = state_id
        if priority is not None:
            input_data["priority"] = priority.value

        result = await self._execute_query(mutation, {"id": issue_id, "input": input_data})
        return result["issueUpdate"]["issue"]

    async def get_members(self) -> List[Dict[str, Any]]:
        """Get all workspace members (for assignee selection)"""
        query = """
        query {
            users {
                nodes { id name email displayName active }
            }
        }
        """
        result = await self._execute_query(query)
        return result.get("users", {}).get("nodes", [])

    # ── Convenience / Dashboard ───────────────────────────────────────

    async def get_dashboard_summary(self, team_id: Optional[str] = None) -> Dict[str, Any]:
        """Get a summary of issues for a dashboard view"""
        all_issues = await self.get_issues(team_id=team_id, limit=200)

        by_state: Dict[str, int] = {}
        by_label: Dict[str, int] = {}
        by_priority: Dict[int, int] = {}
        overdue = 0
        today = datetime.now().strftime("%Y-%m-%d")

        for issue in all_issues:
            # Count by state
            state = issue.get("state", {}).get("name", "Unknown")
            by_state[state] = by_state.get(state, 0) + 1

            # Count by label
            for label in issue.get("labels", {}).get("nodes", []):
                lname = label["name"]
                by_label[lname] = by_label.get(lname, 0) + 1

            # Count by priority
            p = issue.get("priority", 0)
            by_priority[p] = by_priority.get(p, 0) + 1

            # Overdue
            dd = issue.get("dueDate")
            if dd and dd < today and issue.get("state", {}).get("type") != "completed":
                overdue += 1

        return {
            "total_issues": len(all_issues),
            "by_state": by_state,
            "by_label": by_label,
            "by_priority": by_priority,
            "overdue": overdue,
            "recent_issues": all_issues[:10],
        }
