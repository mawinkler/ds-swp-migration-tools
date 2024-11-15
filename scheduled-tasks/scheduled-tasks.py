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
from typeguard import typechecked

# Comment out if DS is using a trusted certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DOCUMENTATION = """
---
module: scheduled-tasks.py

short_description: Implements for following functionality:
    - List Scheduled Tasks in DS and SWP
    - Merge Scheduled Tasks from DS with SWP and vice versa

description:
    - Using REST APIs of DS and SWP

requirements:
    - Set environment variable API_KEY_SWP with the API key of the
      Server & Workload Security instance to use.
    - Set environment variable API_KEY_DS with the API key of the
      Deep Security instance to use.
    - Adapt the constants in between
      # HERE
      and
      # /HERE
      to your requirements

options:
  -h, --help           show this help message and exit
  --listtasks TYPE     list scheduled tasks (TYPE=ds|swp)
  --mergetasks TYPE    merge scheduled tasks from given source (TYPE=ds|swp)

author:
    - Markus Winkler (markus_winkler@trendmicro.com)
"""

EXAMPLES = """
# Merge Scheduled Tasks from DS to SWP
$ ./scheduled-tasks.py --mergegroups ds

# List Scheduled Tasks in SWP
$ ./scheduled-tasks.py --listfolders swp
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

# HERE
REGION_SWP = "us-1."  # Examples: de-1. sg-1.
API_BASE_URL_DS = f"https://3.120.149.217:4119/api/"
# /HERE

# Do not change
ENDPOINT_SWP = "swp"
ENDPOINT_DS = "ds"
API_KEY_SWP = os.environ["API_KEY_SWP"]
API_BASE_URL_SWP = f"https://workload.{REGION_SWP}cloudone.trendmicro.com/api/"
API_KEY_DS = os.environ["API_KEY_DS"]
REQUESTS_TIMEOUTS = (2, 30)
# /Do not change


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
        self._smartfolders = None
        self._reporttemplates = None
        self._administrators = None
        self._contacts = None

        # SWP / DS
        if endpoint == ENDPOINT_SWP:
            self._url = f"{API_BASE_URL_SWP}"
            self._headers = {
                "Content-type": "application/json",
                "api-secret-key": API_KEY_SWP,
                "api-version": "v1",
            }
            self._verify = True

        elif endpoint == ENDPOINT_DS:
            self._url = f"{API_BASE_URL_DS}"
            self._headers = {
                "Content-type": "application/json",
                "Accept": "application/json",
                "api-secret-key": API_KEY_DS,
                "api-version": "v1",
            }
            self._verify = False

        else:
            raise ValueError(f"Invalid endpoint: {endpoint}")

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
                # if item.get("cloudType") is None and item.get("type") != "aws-account":
                paged[item.get("ID")] = item

            id_value = response[key][-1]["ID"]

            if num_found == 0:
                break

            total_num = total_num + num_found

        return paged

    @property
    def computers(self, id=None):
        if self._computers is None:
            self._computers = self.get_paged("computers", "computers")
        return self._computers

    @property
    def policies(self, id=None):
        if self._policies is None:
            self._policies = self.get_paged("policies", "policies")
        return self._policies

    @property
    def computergroups(self, id=None):
        if self._computergroups is None:
            self._computergroups = self.get_paged("computergroups", "computerGroups")
        return self._computergroups

    @property
    def smartfolders(self, id=None):
        if self._smartfolders is None:
            self._smartfolders = self.get_paged("smartfolders", "smartFolders")
        return self._smartfolders

    @property
    def reporttemplates(self, id=None):
        if self._reporttemplates is None:
            self._reporttemplates = self.get_paged("reporttemplates", "reportTemplates")
        return self._reporttemplates

        self._administrators = None
        self._contacts = None

    @property
    def administrators(self, id=None):
        if self._administrators is None:
            self._administrators = self.get_paged("administrators", "administrators")
        return self._administrators

    @property
    def contacts(self, id=None):
        if self._contacts is None:
            self._contacts = self.get_paged("contacts", "contacts")
        return self._contacts

    @typechecked
    def get_by_name(self, endpoint, key, name) -> int:
        """Retrieve by name"""

        # We limit to more than one to detect duplicates by name
        max_items = 2

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

        response = self.post(endpoint + "/search", data=payload)

        cnt = len(response[key])
        if cnt == 1:
            item = response[key][0]
            if item.get("ID") is not None:
                return item.get("ID")
        elif cnt > 1:
            _LOGGER.warning(f"More than one scheduled tasks where returned. Count {len(response[key])}")
            # endpoint_groups = self.get_paged(endpoint, key)

        else:
            raise ValueError(f"Scheduled Task named {name} not found.")

    # @typechecked
    # def get_group_by_name_and_parent(self, endpoint, key, name, parent_id) -> int:
    #     """Retrieve all"""

    #     # We limit to more than one to detect duplicates by name
    #     max_items = 2

    #     if parent_id is None:
    #         payload = {
    #             "maxItems": max_items,
    #             "searchCriteria": [
    #                 {
    #                     "fieldName": "name",
    #                     "stringTest": "equal",
    #                     "stringValue": name,
    #                 }
    #             ],
    #             "sortByObjectID": "true",
    #         }
    #     else:
    #         if key == "computerGroups":
    #             parent_field = "parentGroupID"
    #         elif key == "smartFolders":
    #             parent_field = "parentSmartFolderID"
    #         else:
    #             raise ValueError(f"Invalid key: {key}")

    #         payload = {
    #             "maxItems": max_items,
    #             "searchCriteria": [
    #                 {
    #                     "fieldName": "name",
    #                     "stringTest": "equal",
    #                     "stringValue": name,
    #                 },
    #                 {
    #                     "fieldName": parent_field,
    #                     "numericTest": "equal",
    #                     "numericValue": parent_id,
    #                 },
    #             ],
    #             "sortByObjectID": "true",
    #         }

    #     response = self.post(endpoint + "/search", data=payload)

    #     cnt = len(response[key])
    #     if cnt == 1:
    #         item = response[key][0]
    #         if item.get("ID") is not None:
    #             return item.get("ID")
    #     elif cnt > 1:
    #         _LOGGER.warning(f"More than one group or folder where returned. Count {len(response[key])}")
    #         # endpoint_groups = self.get_paged(endpoint, key)

    #     else:
    #         raise ValueError(f"Group or folder named {name} not found.")

    # @typechecked
    # def get_by_field(self, endpoint, key, field, name) -> int:
    #     """Retrieve by name"""

    #     # We limit to more than one to detect duplicates by name
    #     max_items = 2

    #     payload = {
    #         "maxItems": max_items,
    #         "searchCriteria": [
    #             {
    #                 "fieldName": field,
    #                 "stringTest": "equal",
    #                 "stringValue": name,
    #             }
    #         ],
    #         "sortByObjectID": "true",
    #     }

    #     response = self.post(endpoint + "/search", data=payload)

    #     cnt = len(response[key])
    #     if cnt == 1:
    #         item = response[key][0]
    #         if item.get("ID") is not None:
    #             return item.get("ID")
    #     elif cnt > 1:
    #         _LOGGER.warning(f"More than one scheduled tasks where returned. Count {len(response[key])}")
    #         # endpoint_groups = self.get_paged(endpoint, key)

    #     else:
    #         raise ValueError(f"Scheduled Task named {name} not found.")

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
                    # _LOGGER.error(f"{tre.message}")
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
def list_scheduled_tasks(product, key="scheduledTasks") -> Dict:
    """List Scheduled Tasks."""

    endpoint = "scheduledtasks"
    if product == ENDPOINT_SWP:
        response = connector_swp.get_paged(endpoint=endpoint, key=key)

    elif product == ENDPOINT_DS:
        response = connector_ds.get_paged(endpoint=endpoint, key=key)

    else:
        raise ValueError(f"Invalid endpoint: {product}")

    return response


# #############################################################################
# Add
# #############################################################################
@typechecked
def add_scheduled_task(target, data) -> int:
    """Add Scheduled Task."""

    endpoint = "scheduledtasks"

    data.pop("ID")
    try:
        response = target.post(endpoint=endpoint, data=data)
    except TrendRequestError as tre:
        if "already exists" in tre.message:
            id = target.get_by_name(endpoint=endpoint, key="scheduledTasks", name=data.get("name"))
            _LOGGER.info(f"Scheduled task with name: {data.get("name")} already exists with id: {id}")
            return id
        else:
            raise tre

    # if product == ENDPOINT_SWP:
    #     data.pop("ID")
    #     try:
    #         response = connector_swp.post(endpoint=endpoint, data=data)
    #     except TrendRequestError as tre:
    #         if "already exists" in tre.message:
    #             id = connector_swp.get_by_name(
    #                 endpoint=endpoint, key="scheduledTasks", name=data.get("name")
    #             )
    #             _LOGGER.debug(f"Scheduled task with name: {data.get("name")} already exists with id: {id}")
    #             return id
    #         else:
    #             raise tre

    # elif product == ENDPOINT_DS:
    #     data.pop("ID")
    #     try:
    #         response = connector_ds.post(endpoint=endpoint, data=data)
    #     except TrendRequestError as tre:
    #         if "already exists" in tre.message:
    #             id = connector_ds.get_by_name(
    #                 endpoint=endpoint, key="scheduledTasks", name=data.get("name")
    #             )
    #             _LOGGER.debug(f"Scheduled task with name: {data.get("name")} already exists with id: {id}")
    #             return id
    #         else:
    #             raise tre
    # else:
    #     raise ValueError(f"Invalid endpoint: {product}")

    return response.get("ID")


# #############################################################################
# Merge
# #############################################################################
def merge_scheduled_tasks(product, data, taskprefix="", policysuffix="") -> None:
    """Unidirectional merge Scheduled Tasks"""

    merged = []
    remaining = list(data.keys())

    if product == ENDPOINT_SWP:
        source = connector_swp
        target = connector_ds  # ENDPOINT_DS

    elif product == ENDPOINT_DS:
        source = connector_ds
        target = connector_swp  # ENDPOINT_SWP

    else:
        raise ValueError(f"Invalid endpoint: {product}")

    _LOGGER.debug(f"Task prefix: {taskprefix}, Policy suffix: {policysuffix}")
    for item in data.values():
        # print("---------------------------------------")
        # pp(item)
        source_taskID = item.get("ID")
        _LOGGER.info(f"Processing Scheduled Task: {item.get("name")} with ID: {source_taskID}")
        item["name"] = f"{taskprefix} {item["name"]}"

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

            # pp(item)

            _LOGGER.info(f"Adding Scheduled Task: {item.get("name")}")
            target_taskID = add_scheduled_task(target, item)
            # print("+++++++++++++++++++++++++++++++++++++++")
            merged.append(target_taskID)
            remaining.remove(source_taskID)
        except ValueError as ve:
            _LOGGER.error(ve)

    _LOGGER.debug(f"Merged: {merged}")
    _LOGGER.debug(f"Remaining: {remaining}")
    if len(remaining) > 0:
        _LOGGER.warning(f"{len(remaining)} Scheduled Tasks to create")


# #############################################################################
# Mappers
# #############################################################################
def map_computerFilter(source, target, data, policysuffix="") -> Dict:

    # "computerFilter": {
    #     "type": "computer",
    #     "computerID": 0,
    #     "computerGroupID": 0,
    #     "policyID": 0,
    #     "smartFolderID": 0
    #     }

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


def map_computerGroup(source, target, data) -> Dict:

    # "computerGroupID": 0,

    params = {}

    computerGroupID = None

    # Map the computerGroupID based on name and eventual parent name
    if "computerGroupID" in data:
        computerGroupID = map_computerFilter_computerGroupID(source, target, data, policysuffix="")

    params = {}
    if computerGroupID is not None:
        params["computerGroupID"] = computerGroupID

    return params


def map_recipients(source, target, data) -> Dict:

    # "recipients": {
    #     "allAdministratorsAndContacts": true,
    #     "administratorIDs": [
    #         0
    #     ],
    #     "contactIDs": [
    #         0
    #     ]
    # },

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


def map_computerFilter_computerID(source, target, data) -> Dict:

    computerID = None

    # Map the computerID based on biosUUID
    source_biosUUID = source.computers[data.get("computerID")].get("biosUUID")
    for computer in target.computers.values():
        if computer.get("biosUUID") == source_biosUUID:
            _LOGGER.debug(f"Successful Computer match: {data.get("computerID")} -> {computer.get("ID")}")
            computerID = computer.get("ID")
            break

    if computerID is None:
        raise ValueError(f"Unsuccessful Computer match: {data.get("computerID")}")

    return computerID


def map_computerFilter_computerGroupID(source, target, data) -> Dict:

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
                _LOGGER.debug(f"Successful Computer Group match: {data.get("computerGroupID")} -> {target_groupID}")
                computerGroupID = target_groupID
                break

    if computerGroupID is None:
        raise ValueError(f"Unsuccessful Computer Group match: {data.get("computerGroupID")}")

    return computerGroupID


def map_computerFilter_policyID(source, target, data, policysuffix="") -> Dict:

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
                _LOGGER.debug(f"Successful Policy match: {data.get("policyID")} -> {target_policyID}")
                policyID = target_policyID
                break

    if policyID is None:
        raise ValueError(f"Unsuccessful Policy match: {data.get("policyID")}")

    return policyID


def map_computerFilter_smartFolderID(source, target, data) -> Dict:

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
                _LOGGER.debug(f"Successful Smart Folder match: {data.get("smartFolderID")} -> {target_smartFolderID}")
                smartFolderID = target_smartFolderID
                break

    if smartFolderID is None:
        raise ValueError(f"Unsuccessful Smart Folder match: {data.get("smartFolderID")}")

    return smartFolderID


def map_recipients_administratorIDs(source, target, data) -> Dict:

    administratorIDs = None

    _LOGGER.warning(f"Unable to match Administrators, ignored: {data.get("administratorIDs")}")
    # administratorIDs = []
    # for id in data.get("administratorIDs"):
    #     emailAddress = source.administrators[id].get("emailAddress")
    #     if emailAddress is not None:
    #         targetAdministratorID = None
    #         for administrator in target.administrators.values():
    #             if administrator.get("emailAddress") == emailAddress:
    #                 _LOGGER.debug(f"Successful Administrator match: {data.get("ID")} -> {administrator.get("ID")}")
    #                 targetAdministratorID = administrator.get("ID")
    #                 administratorIDs.append(administrator.get("ID"))
    #                 break

    #         if targetAdministratorID is None:
    #             _LOGGER.error(f"Unsuccessful Administrator match: {id}")

    return administratorIDs


def map_recipients_contactIDs(source, target, data) -> Dict:

    contactIDs = None

    for id in data.get("contactIDs"):
        emailAddress = source.contacts[id].get("emailAddress")
        if emailAddress is not None:
            targetContactID = None
            for contact in target.contacts.values():
                if contact.get("emailAddress") == emailAddress:
                    _LOGGER.debug(f"Successful Contact match: {id} -> {contact.get("ID")}")
                    targetContactID = contact.get("ID")
                    if contactIDs is None:
                        contactIDs = []
                    contactIDs.append(contact.get("ID"))
                    break

            if targetContactID is None:
                raise ValueError(f"Unsuccessful Contact match: {id}")

    return contactIDs


# #############################################################################
# Main
# #############################################################################
# Connectors
connector_ds = Connector(ENDPOINT_DS)
connector_swp = Connector(ENDPOINT_SWP)


def main() -> None:
    """Entry point."""

    parser = argparse.ArgumentParser(
        prog="python3 scheduled-tasks.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="List and merge Scheduled Tasks in between DS and SWP",
        epilog=textwrap.dedent(
            """\
            Examples:
            --------------------------------
            # Merge Scheduled Tasks from DS with SWP
            $ ./scheduled-tasks.py --mergetasks ds --policysuffix " (2024-11-14T16:26:36Z 10.0.0.84)" --taskprefix "DS"

            # List Scheduled Tasks in SWP
            $ ./scheduled-tasks.py --listtasks swp
            """
        ),
    )
    parser.add_argument("--listtasks", type=str, nargs=1, metavar="TYPE", help="list scheduled tasks (TYPE=ds|swp)")
    parser.add_argument(
        "--mergetasks", type=str, nargs=1, metavar="TYPE", help="merge scheduled tasks from given source (TYPE=ds|swp)"
    )
    parser.add_argument("--policysuffix", type=str, default="", help="Optional policy name suffix.")
    parser.add_argument("--taskprefix", type=str, default="", help="Optional task name prefix.")

    args = parser.parse_args()

    # pp(connector_ds.computers)
    # pp(connector_swp.smartfolders)
    # pp(connector_ds.administrators)
    # pp(connector_ds.contacts)
    # pp(connector_swp.contacts)

    if args.listtasks:
        tasks = list_scheduled_tasks(args.listtasks[0].lower())
        for task in tasks.values():
            pp(task)

    if args.mergetasks:
        tasks = list_scheduled_tasks(args.mergetasks[0].lower())
        merge_scheduled_tasks(args.mergetasks[0].lower(), tasks, args.taskprefix, args.policysuffix)


if __name__ == "__main__":
    main()
