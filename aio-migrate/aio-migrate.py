#!/usr/bin/env python3
import argparse
import json
import logging
import os
import sys
import textwrap
from pprint import pprint as pp
from typing import Any, Dict, List

import requests
import urllib3
import yaml
from typeguard import typechecked

# Comment out if DS is using a trusted certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DOCUMENTATION = """
---
module: aio-migrate.py

short_description: Implements for following functionality:
    - List Computer Groups in DS and SWP
    - List Smart Folders in DS and SWP
    - Merge Computer Group structure from DS with SWP and vice versa
    - Merge Smart Folders structure from DS with SWP and vice versa

description:
    - Using REST APIs of DS and SWP

requirements:
    - See READNE.md

options:
  -h, --help            show this help message and exit
  --list                List configured endpoints
  --groups              List or manage computer groups
  --folders             List or manage smart folders
  --scheduled-tasks     List or manage scheduled tasks
  --event-based-tasks   List or manage event-based tasks
  --destination [DESTINATION-ID]
                        Destination Id
  --policysuffix POLICYSUFFIX
                        Optional policy name suffix.
  --taskprefix TASKPREFIX
                        Optional task name prefix.

author:
    - Markus Winkler (markus_winkler@trendmicro.com)
"""

EXAMPLES = """
# List configured endpoints and their IDs
$ ./aio-migrate.py --list

# List Smart Folders from endpoint 2 (SWP DE-1)
$ ./aio-migrate.py --folders 2

# Migrate Computer Groups from endpoint 1 (SWP US-1) to endpoint 2 (SWP DE-1)
$ ./aio-migrate.py --groups 1 --destination 2

# Migrate Scheduled Tasks from endpoint 1 (SWP US-1) to endpoint 2 (SWP DE-1)
$ ./aio-migrate.py --scheduled-tasks 1 --destination 2
"""

RETURN = """
None
"""


_LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s (%(threadName)s) [%(funcName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

ENDPOINT_TYPE_SWP = "swp"
ENDPOINT_TYPE_DS = "ds"
REQUESTS_TIMEOUTS = (2, 30)


# #############################################################################
# Errors
# #############################################################################
class TrendRequestError(Exception):
    """Define a base error."""

    pass


class TrendRequestAuthorizationError(TrendRequestError):
    """Define an error related to invalid API Permissions."""

    pass


class TrendRequestValidationError(TrendRequestError):
    """Define an error related to a validation error from a request."""

    pass


class TrendRequestNotFoundError(TrendRequestError):
    """Define an error related to requested information not found."""

    pass


# #############################################################################
# Connector to SWP/DS
# #############################################################################
class Connector:
    def __init__(self, endpoint) -> None:
        # # V1
        # self._headers = {
        #     "Authorization": f"Bearer {API_KEY_SWP}",
        #     "Content-Type": "application/json;charset=utf-8",
        # }

        self._computers = None
        self._policies = None
        self._computergroups = None
        self._relaygroups = None
        self._smartfolders = None
        self._reporttemplates = None
        self._administrators = None
        self._contacts = None
        self._roles = None

        self._id = endpoint.get("id")
        self._type = endpoint.get("type")
        self._api_key = endpoint.get("api_key")
        self._url = endpoint.get("url")

        # SWP / DS
        if endpoint.get("type") == ENDPOINT_TYPE_SWP:
            self._headers = {
                "Content-type": "application/json",
                "api-secret-key": self._api_key,
                "api-version": "v1",
            }
            self._verify = True

        elif endpoint.get("type") == ENDPOINT_TYPE_DS:
            self._headers = {
                "Content-type": "application/json",
                "Accept": "application/json",
                "api-secret-key": self._api_key,
                "api-version": "v1",
            }
            self._verify = False

        else:
            raise ValueError(f"Invalid endpoint: {endpoint}")

    @property
    def url(self):
        return self._url

    @property
    def type(self):
        return self._type

    @property
    def id(self):
        return self._id

    @property
    def api_key(self):
        return self._api_key

    def get(self, endpoint) -> Any:
        """Send an HTTP GET request and check response for errors.

        Args:
            url (str): API Endpoint
        """

        response = None
        try:
            response = requests.get(
                self._url + endpoint, headers=self._headers, verify=self._verify, timeout=REQUESTS_TIMEOUTS
            )
            self._check_error(response)
            response.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            _LOGGER.error(errh.args[0])
            raise
        except requests.exceptions.ReadTimeout:
            _LOGGER.error("Time out")
            raise
        except requests.exceptions.ConnectionError:
            _LOGGER.error("Connection error")
            raise
        except requests.exceptions.RequestException:
            _LOGGER.error("Exception request")
            raise

        return response.json()

    def patch(self, endpoint, data) -> Any:
        """Send an HTTP PATCH request and check response for errors.

        Args:
            url (str): API Endpoint
            data (json): PATCH request body.
        """

        response = None
        try:
            response = requests.patch(
                self._url + endpoint,
                data=json.dumps(data),
                headers=self._headers,
                verify=self._verify,
                timeout=REQUESTS_TIMEOUTS,
            )
            self._check_error(response)
            response.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            _LOGGER.error(errh.args[0])
            raise
        except requests.exceptions.ReadTimeout:
            _LOGGER.error("Time out")
            raise
        except requests.exceptions.ConnectionError:
            _LOGGER.error("Connection error")
            raise
        except requests.exceptions.RequestException:
            _LOGGER.error("Exception request")
            raise

        return response.json()

    def post(self, endpoint, data) -> Any:
        """Send an HTTP POST request and check response for errors.

        Args:
            url (str): API Endpoint
            data (json): POST request body.
        """

        response = None
        try:
            response = requests.post(
                self._url + endpoint,
                data=json.dumps(data),
                headers=self._headers,
                verify=self._verify,
                timeout=REQUESTS_TIMEOUTS,
            )
            self._check_error(response)
            response.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            _LOGGER.error(errh.args[0])
            raise
        except requests.exceptions.ReadTimeout:
            _LOGGER.error("Time out")
            raise
        except requests.exceptions.ConnectionError:
            _LOGGER.error("Connection error")
            raise
        except requests.exceptions.RequestException:
            _LOGGER.error("Exception request")
            raise

        return response.json()

    @typechecked
    def get_paged(self, endpoint, key) -> Dict:
        """Retrieve all from endpoint"""

        paged = {}
        id_value, total_num = 0, 0
        max_items = 100

        while True:
            payload = {
                "maxItems": max_items,
                "searchCriteria": [
                    {
                        "idValue": id_value,
                        "idTest": "greater-than",
                    }
                ],
                "sortByObjectID": "true",
            }

            response = self.post(endpoint + "/search", data=payload)

            num_found = len(response[key])
            if num_found == 0:
                break

            for item in response[key]:
                # Filter out groups from cloud providers
                # TODO: validate checks
                if item.get("cloudType") is None and item.get("type") != "aws-account":
                    paged[item.get("ID")] = item

            id_value = response[key][-1]["ID"]

            if num_found == 0:
                break

            total_num = total_num + num_found

        return paged

    @typechecked
    def get_by_name(self, endpoint, key, name, parent_id=None) -> int:
        """Retrieve all"""

        # We limit to more than one to detect duplicates by name
        max_items = 2

        if parent_id is None:
            payload = {
                "maxItems": max_items,
                "searchCriteria": [
                    {
                        "fieldName": "name",
                        "stringTest": "equal",
                        "stringValue": name,
                    }
                ],
                "sortByObjectID": "true",
            }
        else:
            if key == "computerGroups":
                parent_field = "parentGroupID"
            elif key == "smartFolders":
                parent_field = "parentSmartFolderID"
            else:
                raise ValueError(f"Invalid key: {key}")

            payload = {
                "maxItems": max_items,
                "searchCriteria": [
                    {
                        "fieldName": "name",
                        "stringTest": "equal",
                        "stringValue": name,
                    },
                    {
                        "fieldName": parent_field,
                        "numericTest": "equal",
                        "numericValue": parent_id,
                    },
                ],
                "sortByObjectID": "true",
            }

        response = self.post(endpoint + "/search", data=payload)

        cnt = len(response[key])
        if cnt == 1:
            item = response[key][0]
            if item.get("ID") is not None:
                return item.get("ID")
        elif cnt > 1:
            _LOGGER.warning(f"More than one group or folder where returned. Count {len(response[key])}")
            # endpoint_groups = self.get_paged(endpoint, key)

        else:
            raise ValueError(f"Group or folder named {name} not found.")

    @property
    def computers(self, id=None) -> Dict:
        if self._computers is None:
            self._computers = self.get_paged("computers", "computers")
        return self._computers

    @property
    def policies(self, id=None) -> Dict:
        if self._policies is None:
            self._policies = self.get_paged("policies", "policies")
        return self._policies

    @property
    def computergroups(self, id=None) -> Dict:
        if self._computergroups is None:
            self._computergroups = self.get_paged("computergroups", "computerGroups")
        return self._computergroups

    @property
    def relaygroups(self, id=None) -> Dict:
        if self._relaygroups is None:
            self._relaygroups = self.get_paged("relaygroups", "relayGroups")
        return self._relaygroups

    @property
    def smartfolders(self, id=None) -> Dict:
        if self._smartfolders is None:
            self._smartfolders = self.get_paged("smartfolders", "smartFolders")
        return self._smartfolders

    @property
    def reporttemplates(self, id=None) -> Dict:
        if self._reporttemplates is None:
            self._reporttemplates = self.get_paged("reporttemplates", "reportTemplates")
        return self._reporttemplates

    @property
    def administrators(self, id=None) -> Dict:
        if self._administrators is None:
            self._administrators = self.get_paged("administrators", "administrators")
        return self._administrators

    @property
    def contacts(self, id=None) -> Dict:
        if self._contacts is None:
            self._contacts = self.get_paged("contacts", "contacts")
        return self._contacts

    @property
    def roles(self, id=None) -> Dict:
        if self._roles is None:
            self._roles = self.get_paged("roles", "roles")
        return self._roles

    @staticmethod
    def _check_error(response: requests.Response) -> None:
        """Check response for Errors.

        Args:
            response (Response): Response to check.
        """

        if not response.ok:
            match response.status_code:
                case 400:
                    tre = TrendRequestError("400 Bad request")
                    tre.message = json.loads(response.content.decode("utf-8")).get("message")
                    _LOGGER.error(f"{tre.message}")
                    raise tre
                case 401:
                    raise TrendRequestAuthorizationError(
                        "401 Unauthorized. The requesting user does not have enough privilege."
                    )
                case 403:
                    raise TrendRequestAuthorizationError(
                        "403 Forbidden. The requesting user does not have enough privilege."
                    )
                case 404:
                    raise TrendRequestNotFoundError("404 Not found")
                case 422:
                    raise TrendRequestValidationError("500 Unprocessed Entity. Validation error")
                case 500:
                    raise TrendRequestError("500 The parsing of the template file failed")
                case 503:
                    raise TrendRequestError("503 Service unavailable")
                case _:
                    raise TrendRequestError(response.text)


# #############################################################################
# List
# #############################################################################
@typechecked
def list_groups(connector) -> Dict:
    """List Computer Groups."""

    endpoint = "computergroups"

    return connector.get_paged(endpoint=endpoint, key="computerGroups")


@typechecked
def list_folders(connector) -> Dict:
    """List Smart Folders."""

    endpoint = "smartfolders"

    return connector.get_paged(endpoint=endpoint, key="smartFolders")


@typechecked
def list_scheduled_tasks(connector, key="scheduledTasks") -> Dict:
    """List Scheduled Tasks."""

    endpoint = "scheduledtasks"

    response = connector.get_paged(endpoint=endpoint, key=key)

    return response


@typechecked
def list_event_based_tasks(connector, key="eventBasedTasks") -> Dict:
    """List Event Based Tasks."""

    endpoint = "eventbasedtasks"

    response = connector.get_paged(endpoint=endpoint, key=key)

    return response


# #############################################################################
# Add
# #############################################################################
@typechecked
def add_group(connector, data) -> int:
    """Add Computer Group."""

    endpoint = "computergroups"

    data.pop("ID")
    try:
        response = connector.post(endpoint=endpoint, data=data)
    except TrendRequestError as tre:
        if "already exists" in tre.message:
            id = connector.get_by_name(
                endpoint=endpoint, key="computerGroups", name=data.get("name"), parent_id=data.get("parentGroupID")
            )
            _LOGGER.debug(f"Group with name: {data.get('name')} already exists with id: {id}")
            return id
        else:
            raise tre

    return response.get("ID")


@typechecked
def add_folder(connector, data) -> int:
    """Add Smart Folder."""

    endpoint = "smartfolders"

    data.pop("ID")
    try:
        response = connector.post(endpoint=endpoint, data=data)
    except TrendRequestError as tre:
        if "already exists" in tre.message:
            id = connector.get_by_name(
                endpoint=endpoint,
                key="smartFolders",
                name=data.get("name"),
                parent_id=data.get("parentSmartFolderID"),
            )
            _LOGGER.debug(f"Smart Folder with name: {data.get('name')} already exists with id: {id}")
            return id
        else:
            raise tre

    return response.get("ID")


@typechecked
def add_scheduled_task(connector, data) -> int:
    """Add Scheduled Task."""

    endpoint = "scheduledtasks"

    task_type = data.get("type", None)
    if connector.type == ENDPOINT_TYPE_SWP and task_type is not None and task_type == "check-for-software-updates":
        _LOGGER.info(f"Scheduled task: Task type {task_type} not supported in Server & Workload Protection. Skipping.")
        return None

    data.pop("ID")
    try:
        response = connector.post(endpoint=endpoint, data=data)
    except TrendRequestError as tre:
        if "already exists" in tre.message:
            id = connector.get_by_name(endpoint=endpoint, key="scheduledTasks", name=data.get("name"))
            _LOGGER.info(f"Scheduled task with name: {data.get('name')} already exists with id: {id}")
            return id
        else:
            raise tre

    return response.get("ID")


@typechecked
def add_event_based_task(connector, data) -> int:
    """Add Event Based Task."""

    endpoint = "eventbasedtasks"

    data.pop("ID")
    try:
        response = connector.post(endpoint=endpoint, data=data)
    except TrendRequestError as tre:
        if "must be unique" in tre.message:
            id = connector.get_by_name(endpoint=endpoint, key="eventBasedTasks", name=data.get("name"))
            _LOGGER.info(f"Event Based task with name: {data.get('name')} already exists with id: {id}")
            return id
        else:
            raise tre

    return response.get("ID")


@typechecked
def add_contact(connector, data) -> int:
    """Add Contact."""

    endpoint = "contacts"

    data.pop("ID")
    # Get roleID for Auditor in target environment
    for role in connector.roles.values():
        if role.get("v1RoleName") == "Auditor":
            data["roleID"] = role.get("ID")
            break

    try:
        response = connector.post(endpoint=endpoint, data=data)
    except TrendRequestError as tre:
        if "already exists" in tre.message:
            id = connector.get_by_name(endpoint=endpoint, key="contacts", name=data.get("name"))
            _LOGGER.info(f"Contact with name: {data.get('name')} already exists with id: {id}")
            return id
        else:
            raise tre

    return response.get("ID")


# #############################################################################
# Merge
# #############################################################################
def merge_groups(connector, data) -> None:
    """Unidirectional merge Computer Groups"""

    tree = {}
    remaining = []

    for item in data.values():
        if item.get("parentGroupID") is None:
            local_id = item.get("ID")
            _LOGGER.info(f"Adding root group {local_id}")
            item["name"] = f"{item['name']}"
            tree[local_id] = add_group(connector, item)

        elif item.get("parentGroupID") in tree:
            local_id = item.get("ID")
            parent_id = tree.get(item.get("parentGroupID"))
            _LOGGER.info(f"Adding child group {local_id} to {parent_id}")
            item["parentGroupID"] = parent_id
            item["name"] = f"{item['name']}"
            tree[local_id] = add_group(connector, item)

        else:
            remaining.append(item)

    _LOGGER.debug(f"Group mapping: {tree}")
    if len(remaining) > 0:
        _LOGGER.warning(f"{len(remaining)} groups to create")


def merge_folders(source, target, data, taskprefix="", policysuffix="") -> None:
    """Unidirectional merge Computer Groups"""

    tree = {}
    remaining = []

    for item in data.values():
        rule_groups = item.get("ruleGroups")
        if rule_groups is not None:
            rule_groups_migrated = []
            for rule_group in rule_groups:
                rules_migrated = []
                rules = rule_group.get("rules")
                if rules is not None:
                    for rule in rules:
                        if rule.get("key") == "general-policy":
                            data = {"policyID": int(rule.get("value"))}
                            rule["value"] = str(map_computerFilter(source, target, data, policysuffix).get("policyID"))
                        rules_migrated.append(rule)
                rule_group["rules"] = rules_migrated

                rule_groups_migrated.append(rule_group)
        item["ruleGroups"] = rule_groups_migrated

        if item.get("parentSmartFolderID") is None:
            local_id = item.get("ID")
            _LOGGER.info(f"Adding root folder {local_id}")
            item["name"] = f"{item['name']}"
            tree[local_id] = add_folder(target, item)

        elif item.get("parentSmartFolderID") in tree:
            local_id = item.get("ID")
            parent_id = tree.get(item.get("parentSmartFolderID"))
            _LOGGER.info(f"Adding child folder {local_id} to {parent_id}")
            item["parentSmartFolderID"] = parent_id
            item["name"] = f"{item['name']}"
            tree[local_id] = add_folder(target, item)

        else:
            remaining.append(item)

    _LOGGER.debug(f"Folder mapping: {tree}")
    if len(remaining) > 0:
        _LOGGER.warning(f"{len(remaining)} folders to create")


def merge_scheduled_tasks(source, target, data, taskprefix="", policysuffix="") -> None:
    """Unidirectional merge Scheduled Tasks"""

    merged = []
    remaining = list(data.keys())

    _LOGGER.debug(f"Task prefix: {taskprefix}, Policy suffix: {policysuffix}")
    for item in data.values():
        source_taskID = item.get("ID")
        _LOGGER.info(f"Processing Scheduled Task: {item.get('name')} with ID: {source_taskID}")
        item["name"] = f"{taskprefix}{item['name']}"

        try:
            if "checkForSecurityUpdatesTaskParameters" in item:
                item["checkForSecurityUpdatesTaskParameters"]["computerFilter"] = map_computerFilter(
                    source,
                    target,
                    item.get("checkForSecurityUpdatesTaskParameters").get("computerFilter"),
                    policysuffix,
                )
            if "discoverComputersTaskParameters" in item:
                item["discoverComputersTaskParameters"]["computerFilter"] = map_computerFilter(
                    source, target, item.get("discoverComputersTaskParameters").get("computerFilter"), policysuffix
                )
            if "generateReportTaskParameters" in item:
                item["generateReportTaskParameters"]["recipients"] = map_recipients(
                    source, target, item.get("generateReportTaskParameters").get("recipients")
                )
                item["generateReportTaskParameters"]["computerFilter"] = map_computerFilter(
                    source, target, item.get("generateReportTaskParameters").get("computerFilter"), policysuffix
                )
            if "scanForIntegrityChangesTaskParameters" in item:
                item["scanForIntegrityChangesTaskParameters"]["computerFilter"] = map_computerFilter(
                    source,
                    target,
                    item.get("scanForIntegrityChangesTaskParameters").get("computerFilter"),
                    policysuffix,
                )
            if "scanForMalwareTaskParameters" in item:
                item["scanForMalwareTaskParameters"]["computerFilter"] = map_computerFilter(
                    source, target, item.get("scanForMalwareTaskParameters").get("computerFilter"), policysuffix
                )
            if "scanForOpenPortsTaskParameters" in item:
                item["scanForOpenPortsTaskParameters"]["computerFilter"] = map_computerFilter(
                    source, target, item.get("scanForOpenPortsTaskParameters").get("computerFilter"), policysuffix
                )
            if "scanForRecommendationsTaskParameters" in item:
                item["scanForRecommendationsTaskParameters"]["computerFilter"] = map_computerFilter(
                    source, target, item.get("scanForRecommendationsTaskParameters").get("computerFilter"), policysuffix
                )
            if "sendAlertSummaryTaskParameters" in item:
                item["sendAlertSummaryTaskParameters"]["recipients"] = map_recipients(
                    source, target, item.get("sendAlertSummaryTaskParameters").get("recipients")
                )
            if "sendPolicyTaskParameters" in item:
                item["sendPolicyTaskParameters"]["computerFilter"] = map_computerFilter(
                    source, target, item.get("sendPolicyTaskParameters").get("computerFilter"), policysuffix
                )
            if "synchronizeCloudAccountTaskParameters" in item:
                item["synchronizeCloudAccountTaskParameters"]["computerGroupID"] = map_computerGroup(
                    source, target, item.get("synchronizeCloudAccountTaskParameters").get("computerGroupID")
                )
            if "synchronizeDirectoryTaskParameters" in item:
                item["synchronizeDirectoryTaskParameters"]["computerGroupID"] = map_computerGroup(
                    source, target, item.get("synchronizeDirectoryTaskParameters").get("computerGroupID")
                )
            if "synchronizeVCenterTaskParameters" in item:
                item["synchronizeVCenterTaskParameters"]["computerGroupID"] = map_computerGroup(
                    source, target, item.get("synchronizeVCenterTaskParameters").get("computerGroupID")
                )
            if "updateSuspiciousObjectsListTaskParameters" in item:
                item["updateSuspiciousObjectsListTaskParameters"]["computerFilter"] = map_computerFilter(
                    source,
                    target,
                    item.get("updateSuspiciousObjectsListTaskParameters").get("computerFilter"),
                    policysuffix,
                )
            if "scheduledAgentUpgradeTaskParameters" in item:
                item["scheduledAgentUpgradeTaskParameters"]["computerFilter"] = map_computerFilter(
                    source,
                    target,
                    item.get("scheduledAgentUpgradeTaskParameters").get("computerFilter"),
                    policysuffix,
                )
            if "installV1AgentParameters" in item:
                item["installV1AgentParameters"]["computerFilter"] = map_computerFilter(
                    source,
                    target,
                    item.get("installV1AgentParameters").get("computerFilter"),
                    policysuffix,
                )

            _LOGGER.info(f"Adding Scheduled Task: {item.get('name')}")
            target_taskID = add_scheduled_task(target, item)

            if target_taskID is not None:
                merged.append(target_taskID)
            remaining.remove(source_taskID)
        except ValueError as ve:
            _LOGGER.error(ve)

    _LOGGER.debug(f"Merged: {merged}")
    _LOGGER.debug(f"Remaining: {remaining}")
    if len(remaining) > 0:
        _LOGGER.warning(f"{len(remaining)} Scheduled Tasks to create")


def merge_event_based_tasks(source, target, data, taskprefix="", policysuffix="") -> None:
    """Unidirectional merge Event Based Tasks"""

    merged = []
    remaining = list(data.keys())

    _LOGGER.debug(f"Task prefix: {taskprefix}, Policy suffix: {policysuffix}")
    for item in data.values():
        source_taskID = item.get("ID")
        _LOGGER.info(f"Processing Event Based Task: {item.get('name')} with ID: {source_taskID}")
        item["name"] = f"{taskprefix}{item['name']}"
        target_actions = []
        target_conditions = []
        try:
            actions = item.get("actions", [])
            for action in actions:
                if action.get("type") == "assign-policy":
                    if action.get("parameterValue") is not None:
                        data = {"policyID": action.get("parameterValue")}
                        action["parameterValue"] = map_computerFilter(source, target, data, policysuffix).get(
                            "policyID"
                        )
                if action.get("type") == "assign-relay":
                    _LOGGER.warning("Mapping of Relay Groups is not supported. Removing action.")
                    action["parameterValue"] = None
                if action.get("type") == "assign-group":
                    if action.get("parameterValue") is not None:
                        data = {"computerGroupID": action.get("parameterValue")}
                        action["parameterValue"] = map_computerFilter(source, target, data, policysuffix).get(
                            "computerGroupID"
                        )
                # if action.get("type") == "activate":
                # if action.get("type") == "deactivate":
                target_actions.append(action)

            conditions = item.get("conditions", [])
            for condition in conditions:
                _LOGGER.info(f"Processing Event Based Task Condition: {item.get('name')}: {condition}")
                target_conditions.append(condition)

            item["actions"] = target_actions
            item["conditions"] = target_conditions

            _LOGGER.info(f"Adding Event Based Task: {item.get('name')}")
            target_taskID = add_event_based_task(target, item)

            merged.append(target_taskID)
            remaining.remove(source_taskID)
        except ValueError as ve:
            _LOGGER.error(ve)

    _LOGGER.debug(f"Merged: {merged}")
    _LOGGER.debug(f"Remaining: {remaining}")
    if len(remaining) > 0:
        _LOGGER.warning(f"{len(remaining)} Event Based Tasks to create")


# #############################################################################
# Mappers
# #############################################################################
@typechecked
def map_computerFilter(source, target, data, policysuffix="") -> Dict:
    params = {}

    computerID = None
    computerGroupID = None
    policyID = None
    smartFolderID = None

    # Map the computerID based on biosUUID
    if "computerID" in data:
        computerID = map_computerFilter_computerID(source, target, data)

    # Map the computerGroupID based on name and eventual parent name
    if "computerGroupID" in data:
        computerGroupID = map_computerFilter_computerGroupID(source, target, data)

    # Map the policyID based on name and eventual parent name
    if "policyID" in data:
        policyID = map_computerFilter_policyID(source, target, data, policysuffix)

    # Map the smartFolderID based on name and eventual parent name
    if "smartFolderID" in data:
        smartFolderID = map_computerFilter_smartFolderID(source, target, data)

    params = {
        "type": data.get("type") if "type" in data else "",
    }
    if computerID is not None:
        params["computerID"] = computerID
    if computerGroupID is not None:
        params["computerGroupID"] = computerGroupID
    if policyID is not None:
        params["policyID"] = policyID
    if smartFolderID is not None:
        params["smartFolderID"] = smartFolderID

    return params


@typechecked
def map_computerGroup(source, target, data) -> Dict:
    params = {}

    computerGroupID = None

    # Map the computerGroupID based on name and eventual parent name
    if "computerGroupID" in data:
        computerGroupID = map_computerFilter_computerGroupID(source, target, data, policysuffix="")

    params = {}
    if computerGroupID is not None:
        params["computerGroupID"] = computerGroupID

    return params


@typechecked
def map_recipients(source, target, data) -> Dict:
    params = {}

    administratorIDs = None
    contactIDs = None

    # Map the computerID based on biosUUID
    if "administratorIDs" in data:
        administratorIDs = map_recipients_administratorIDs(source, target, data)

    if "contactIDs" in data:
        contactIDs = map_recipients_contactIDs(source, target, data)

    params = {
        "allAdministratorsAndContacts": (
            data.get("allAdministratorsAndContacts") if "allAdministratorsAndContacts" in data else True
        ),
    }
    if administratorIDs is not None:
        params["administratorIDs"] = administratorIDs
    if contactIDs is not None:
        params["contactIDs"] = contactIDs

    return params


@typechecked
def map_computerFilter_computerID(source, target, data) -> int | None:
    computerID = None

    # Map the computerID based on biosUUID
    source_biosUUID = source.computers[data.get("computerID")].get("biosUUID")
    for computer in target.computers.values():
        if computer.get("biosUUID") == source_biosUUID:
            _LOGGER.debug(f"Successful Computer match: {data.get('computerID')} -> {computer.get('ID')}")
            computerID = computer.get("ID")
            break

    if computerID is None:
        raise ValueError(f"Unsuccessful Computer match: {data.get('computerID')}")

    return computerID


@typechecked
def map_computerFilter_computerGroupID(source, target, data) -> int | None:
    computerGroupID = None

    source_groupName = source.computergroups[data.get("computerGroupID")].get("name")
    source_parentGroupID = source.computergroups[data.get("computerGroupID")].get("parentGroupID")
    source_parentGroupName = None
    if source_parentGroupID is not None:
        source_parentGroupName = source.computergroups[source_parentGroupID].get("name")

    target_parentGroupName = None
    for computergroup in target.computergroups.values():
        target_groupName = computergroup.get("name")
        if target_groupName == source_groupName:
            target_groupID = computergroup.get("ID")
            target_parentGroupID = computergroup.get("parentGroupID")
            if target_parentGroupID is not None:
                target_parentGroupName = target.computergroups[target_parentGroupID].get("name")
            # If we handle a root group both parent names will be None and therefore equal
            if target_groupName == source_groupName and target_parentGroupName == source_parentGroupName:
                _LOGGER.debug(f"Successful Computer Group match: {data.get('computerGroupID')} -> {target_groupID}")
                computerGroupID = target_groupID
                break

    if computerGroupID is None:
        raise ValueError(f"Unsuccessful Computer Group match: {data.get('computerGroupID')}")

    return computerGroupID


@typechecked
def map_computerFilter_policyID(source, target, data, policysuffix="") -> int | None:
    policyID = None

    source_policyName = source.policies[data.get("policyID")].get("name")
    source_parentPolicyID = source.policies[data.get("policyID")].get("parentID")
    source_parentPolicyName = None
    if source_parentPolicyID is not None:
        source_parentPolicyName = source.policies[source_parentPolicyID].get("name")

    target_parentPolicyName = None
    for policy in target.policies.values():
        target_policyName = policy.get("name")
        target_policyName = target_policyName.removesuffix(policysuffix)
        if target_policyName == source_policyName:
            target_policyID = policy.get("ID")
            target_parentPolicyID = policy.get("parentID")
            if target_parentPolicyID is not None:
                target_parentPolicyName = target.policies[target_parentPolicyID].get("name")
                target_parentPolicyName = target_parentPolicyName.removesuffix(policysuffix)
            # If we handle a root policy both parent names will be None and therefore equal
            if target_policyName == source_policyName and target_parentPolicyName == source_parentPolicyName:
                _LOGGER.debug(f"Successful Policy match: {data.get('policyID')} -> {target_policyID}")
                policyID = target_policyID
                break

    if policyID is None:
        raise ValueError(f"Unsuccessful Policy match: {data.get('policyID')}")

    return policyID


@typechecked
def map_computerFilter_relayGroupID(source, target, data, policysuffix="") -> int | None:
    """Not supported"""

    return 0


@typechecked
def map_computerFilter_smartFolderID(source, target, data) -> int | None:
    smartFolderID = None

    source_smartFolderName = source.smartfolders[data.get("smartFolderID")].get("name")
    source_parentSmartFolderID = source.smartfolders[data.get("smartFolderID")].get("parentSmartFolderID")
    source_parentSmartFolderName = None
    if source_parentSmartFolderID is not None:
        source_parentSmartFolderName = source.smartfolders[source_parentSmartFolderID].get("name")

    target_parentSmartFolderName = None
    for smartfolder in target.smartfolders.values():
        target_smartFolderName = smartfolder.get("name")
        if target_smartFolderName == source_smartFolderName:
            target_smartFolderID = smartfolder.get("ID")
            target_parentSmartFolderID = smartfolder.get("parentSmartFolderID")
            if target_parentSmartFolderID is not None:
                target_parentSmartFolderName = target.smartfolders[target_parentSmartFolderID].get("name")
            # If we handle a root smart folders both parent names will be None and therefore equal
            if (
                target_smartFolderName == source_smartFolderName
                and target_parentSmartFolderName == source_parentSmartFolderName
            ):
                _LOGGER.debug(f"Successful Smart Folder match: {data.get('smartFolderID')} -> {target_smartFolderID}")
                smartFolderID = target_smartFolderID
                break

    if smartFolderID is None:
        raise ValueError(f"Unsuccessful Smart Folder match: {data.get('smartFolderID')}")

    return smartFolderID


@typechecked
def map_recipients_administratorIDs(source, target, data) -> List | None:
    administratorIDs = None

    _LOGGER.warning(f"Unable to match Administrators, ignored: {data.get('administratorIDs')}")
    # administratorIDs = []
    # for id in data.get("administratorIDs"):
    #     emailAddress = source.administrators[id].get("emailAddress")
    #     if emailAddress is not None:
    #         targetAdministratorID = None
    #         for administrator in target.administrators.values():
    #             if administrator.get("emailAddress") == emailAddress:
    #                 _LOGGER.debug(f"Successful Administrator match: {data.get('ID')} -> {administrator.get('ID')}")
    #                 targetAdministratorID = administrator.get("ID")
    #                 administratorIDs.append(administrator.get("ID"))
    #                 break

    #         if targetAdministratorID is None:
    #             _LOGGER.error(f"Unsuccessful Administrator match: {id}")

    return administratorIDs


@typechecked
def map_recipients_contactIDs(source, target, data) -> List | None:
    contactIDs = None

    for id in data.get("contactIDs"):
        emailAddress = source.contacts[id].get("emailAddress")
        if emailAddress is not None:
            targetContactID = None
            for contact in target.contacts.values():
                if contact.get("emailAddress") == emailAddress:
                    _LOGGER.debug(f"Successful Contact match: {id} -> {contact.get('ID')}")
                    targetContactID = contact.get("ID")
                    if contactIDs is None:
                        contactIDs = []
                    contactIDs.append(targetContactID)
                    break

            if targetContactID is None:
                targetContactID = add_contact(target, source.contacts[id])
                _LOGGER.info(f"Contact created: {targetContactID} with {emailAddress}")
                contactIDs.append(targetContactID)

    return contactIDs


# #############################################################################
# Main
# #############################################################################
# Connectors
connectors = []
if os.path.isfile("config.yaml"):
    with open("config.yaml", "r", encoding="utf-8") as ymlfile:
        cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)
else:
    cfg = None

for idx, endpoint in enumerate(cfg.get("endpoints")):
    endpoint["id"] = idx
    connectors.append(Connector(endpoint))

_LOGGER.info(f"Connectors initialized: {len(connectors)}")


def main() -> None:
    """Entry point."""

    parser = argparse.ArgumentParser(
        prog="python3 aio-migrate.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="List and migrate objects in between DS and SWP",
        epilog=textwrap.dedent(
            """\
            Examples:
            --------------------------------
            # List configured endpoints
            $ ./aio-migrate.py --list

            # List Smart Folders from endpoint 2
            $ ./aio-migrate.py --folders 2
            
            # Migrate Computer Groups from endpoint 1 to endpoint 2
            $ ./aio-migrate.py --groups 1 --destination 2

            # Migrate Scheduled Tasks from endpoint 1 to endpoint 2
            $ ./aio-migrate.py --scheduled-tasks 1 --destination 2
            """
        ),
    )

    parser.add_argument("--list", action=argparse.BooleanOptionalAction, help="List configured endpoints")
    parser.add_argument("--groups", action=argparse.BooleanOptionalAction, help="List or manage computer groups")
    parser.add_argument("--folders", action=argparse.BooleanOptionalAction, help="List or manage smart folders")
    parser.add_argument(
        "--scheduled-tasks", action=argparse.BooleanOptionalAction, help="List or manage scheduled tasks"
    )
    parser.add_argument(
        "--event-based-tasks", action=argparse.BooleanOptionalAction, help="List or manage event-based tasks"
    )

    parser.add_argument("source", type=int, nargs="?", metavar="SOURCE-ID", help="Source Id")
    parser.add_argument("--destination", type=int, nargs="?", metavar="DESTINATION-ID", help="Destination Id")

    parser.add_argument("--policysuffix", type=str, default="", help="Optional policy name suffix.")
    parser.add_argument("--taskprefix", type=str, default="", help="Optional task name prefix.")

    args = parser.parse_args()

    if args.list:
        for connector in connectors:
            print(
                f"ID: {connector.id + 1}: Type: {connector.type}, Url: {connector.url}, API Key: {connector.api_key[-8:]}"
            )

    if args.groups:
        if args.destination is None:
            groups = list_groups(connectors[args.source - 1])
            for group in groups.values():
                pp(group)
        else:
            groups = list_groups(connectors[args.source - 1])
            merge_groups(connectors[args.destination - 1], groups)

    if args.folders:
        if args.destination is None:
            folders = list_folders(connectors[args.source - 1])
            for folders in folders.values():
                pp(folders)
        else:
            folders = list_folders(connectors[args.source - 1])
            merge_folders(
                connectors[args.source - 1],
                connectors[args.destination - 1],
                folders,
                args.taskprefix,
                args.policysuffix,
            )

    if args.scheduled_tasks:
        if args.destination is None:
            scheduled_tasks = list_scheduled_tasks(connectors[args.source - 1])
            for group in scheduled_tasks.values():
                pp(group)
        else:
            scheduled_tasks = list_scheduled_tasks(connectors[args.source - 1])
            merge_scheduled_tasks(
                connectors[args.source - 1],
                connectors[args.destination - 1],
                scheduled_tasks,
                args.taskprefix,
                args.policysuffix,
            )

    if args.event_based_tasks:
        if args.destination is None:
            event_based_tasks = list_event_based_tasks(connectors[args.source - 1])
            for group in event_based_tasks.values():
                pp(group)
        else:
            event_based_tasks = list_event_based_tasks(connectors[args.source - 1])
            merge_event_based_tasks(
                connectors[args.source - 1],
                connectors[args.destination - 1],
                event_based_tasks,
                args.taskprefix,
                args.policysuffix,
            )


if __name__ == "__main__":
    main()
