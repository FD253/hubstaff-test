#!/usr/bin/python3
import argparse
import datetime
import os
import webbrowser
from collections import defaultdict

import requests
import pandas as pd

from config import AUTH_TOKEN, APP_TOKEN, EMAIL, PASSWORD


class HubStaff:
    AUTH_URL = 'https://api.hubstaff.com/v1/auth'
    USERS_URL = 'https://api.hubstaff.com/v1/users?organization_memberships=true&project_memberships=true'
    CUSTOM_BY_DATE_URL = 'https://api.hubstaff.com/v1/custom/by_date/team?'

    def __init__(self, app_token, email, password, auth_token):
        self.app_token = app_token
        self.email = email
        self.password = password
        self.auth_token = auth_token or self.get_auth_token()

    def get_auth_token(self):
        response = requests.post(
            self.AUTH_URL,
            data={
                'email': self.email,
                'password': self.password
            },
            headers={
                'App-Token': self.app_token
            }
        )
        response.raise_for_status()
        self.auth_token = response.json()['user']['auth_token']
        return self.auth_token

    def get_tokens(self):
        return {'Auth-Token': self.auth_token, 'App-Token': self.app_token}

    def get_organizations_users_and_projects(self):
        response = requests.get(
            self.USERS_URL,
            headers=self.get_tokens()
        )
        response.raise_for_status()
        return response.json()

    def parse_sets(self, _set):
        return ','.join(str(s) for s in _set)

    def get_custom_by_date_team(self, start_date, end_date):
        users_and_their_projects = self.get_organizations_users_and_projects()
        user_ids = []
        project_ids = []
        organization_ids = []
        for user in users_and_their_projects['users']:
            user_ids.append(user['id'])
            for project in user['projects']:
                project_ids.append(project['id'])
            for organization in user['organizations']:
                organization_ids.append(organization['id'])
        organization_ids = set(organization_ids)
        response = requests.get(
            self.CUSTOM_BY_DATE_URL,
            headers=self.get_tokens(),
            params={
                'start_date': start_date,
                'end_date': end_date,
                'organizations': self.parse_sets(organization_ids),
                'projects': self.parse_sets(project_ids),
                'users': self.parse_sets(user_ids)
            }
        )
        response.raise_for_status()
        all_data = response.json()
        projects_and_employees_durations = defaultdict(lambda: defaultdict(str))
        if all_data.get('organizations'):
            organization = all_data.get('organizations')[0]
            if organization.get('dates'):
                date = organization.get('dates')[0]
                for user in date['users']:
                    if user.get('projects'):
                        for project in user.get('projects'):
                            projects_and_employees_durations[user.get('name')][project['name']] = str(
                                datetime.timedelta(seconds=project['duration']))
        return projects_and_employees_durations

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d')
    args = parser.parse_args()

    hs = HubStaff(
        app_token=APP_TOKEN,
        auth_token=AUTH_TOKEN,
        email=EMAIL,
        password=PASSWORD,
    )

    yesterday = (datetime.datetime.today().date()-datetime.timedelta(1)).isoformat()
    parsed_date = None
    if args.d:
        parsed_date = datetime.datetime.strptime(args.d, '%Y-%m-%d')
    all_data = hs.get_custom_by_date_team(start_date=parsed_date or yesterday,
                                          end_date=parsed_date or yesterday)
    with open('table.html', 'w') as f:
        f.write(pd.DataFrame(all_data).to_html())
    filename = 'file:///' + os.getcwd() + '/' + 'table.html'
    webbrowser.open_new_tab(filename)
