import os
from dotenv import load_dotenv
from jira import JIRA
from typing import List
from business_info import BusinessInfo

load_dotenv

class IssueInfo:
    def __init__(
            self,
            key,
            summary,
            description,
            resolution_date,
            business_info = None,
            epic_key = None,
            epic_summary = None):
        self.key = key
        self.summary = summary
        self.description = description
        self.resolution_date = resolution_date
        self.business_info = business_info
        self.epic_key = epic_key
        self.epic_summary = epic_summary
    

    def __repr__(self):
        return (f"IssueInfo(key={self.key}, summary={self.summary!r}, "
                f"epic_key={self.epic_key}, resolved={self.resolution_date})")


class JiraClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JiraClient, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance
    
    def _init_client(self):
        server = os.getenv("JIRA_SERVER")
        user = os.getenv("JIRA_USER")
        token = os.getenv("JIRA_API_TOKEN")
        options = {"server": server}
        self.client = JIRA(options, basic_auth=(user, token))

    def get_issues_from_filter(self, filter_id):
        print(f"Fetching all issues from Jira filter {filter_id}")
        issues = self.client.search_issues(f"filter={filter_id}", maxResults=False)
        print(f"Found {len(issues)} issues.")
        return issues
    
    def proccess_issue_list_info(self, issues) -> List[IssueInfo]:
        info_collection = []
        for issue in issues:
            issue_info = self._get_issue_info(issue)
            info_collection.append(issue_info)

        return info_collection


    
    def _get_issue_info(self, issue) -> IssueInfo:
        issue_key = issue.key
        summary = issue.fields.summary
        description = issue.fields.description
        resolution_date = issue.fields.resolutiondate or "not resolved"
        epic_key = issue.fields.parent.key
        epic_summary = None

        # Agregar información de business info si existe
        business_info = BusinessInfo()
        if epic_key:
            info = business_info.get_business_info(f"{epic_key}")


        return IssueInfo(
            key=issue_key,
            summary=summary,
            description=description,
            resolution_date=resolution_date,
            business_info=info,
            epic_key=epic_key,
            epic_summary=epic_summary
        )
        


