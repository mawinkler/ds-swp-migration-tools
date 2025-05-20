# Deep Security to Server & Workload Protection Migration Tools

> ***Note:***
>
> ***These scripts are work-in-progress and require further testing. Please exercise caution when using them.***

This repo hosts tools to support a migration of

- Computer Groups
- Smart Folders
- Scheduled Tasks
- Event-based Tasks

in between Deep Security or Vision One Server & Workload Protection instances.

Abbreviations used:

- DS: Deep Security
- SWP: Vision One Server & Workload Protection

Get the code:

```sh
git clone https://github.com/mawinkler/ds-swp-migration-tools.git
cd ds-swp-migration-tools/aio-migrate

python3 -m venv venv && source venv/bin/activate

pip install -r requirements.txt
```

## Configuration

In `aio-migrate`, create a `config.yaml` based on the sample provided:

```yaml
endpoints:
  - type: swp
    url: https://workload.us-1.cloudone.trendmicro.com/api/
    api_key: <SWP API KEY>
  - type: swp
    url: https://workload.de-1.cloudone.trendmicro.com/api/
    api_key: <SWP API KEY>
  - type: ds
    url: https://<IP OF DSM>:4119/api/
    api_key: <DS API KEY>
```

## Entpoint IDs

The script supports multiple endpoints, i.e. instances of SWP and DS. Different actions offered by the script require endpoint IDs to determine which endpoint data should be migrated to which other endpoint. To retrieve the endpoint IDs, run the following command:

```sh
./aio-migrate.py --list
```

```sh
2025-05-20 10:58:16 INFO (MainThread) [<module>] Connectors initialized: 3
ID: 1: Type: swp, Url: https://workload.us-1.cloudone.trendmicro.com/api/, API Key: d24XUMI=
ID: 2: Type: swp, Url: https://workload.de-1.cloudone.trendmicro.com/api/, API Key: +4mWcvA=
ID: 3: Type: ds, Url: https://3.120.149.217:4119/api/, API Key: Wpm89MA=
```

## Get Help

Run:
```sh
./aio-migrate.py --help
```

```sh
2025-05-19 15:38:49 INFO (MainThread) [<module>] Connectors initialized: 3
usage: python3 aio-migrate.py [-h] [--list | --no-list] [--groups | --no-groups] [--folders | --no-folders] [--scheduled-tasks | --no-scheduled-tasks] [--event-based-tasks | --no-event-based-tasks] [--destination [DESTINATION-ID]] [--policysuffix POLICYSUFFIX] [--taskprefix TASKPREFIX] [SOURCE-ID]

List and migrate objects in between DS and SWP

positional arguments:
  SOURCE-ID             Source Id

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

Examples:
--------------------------------
# List configured endpoints and their IDs
$ ./aio-migrate.py --list

# List Smart Folders from endpoint 2 (SWP DE-1)
$ ./aio-migrate.py --folders 2

# Migrate Computer Groups from endpoint 1 (SWP US-1) to endpoint 2 (SWP DE-1)
$ ./aio-migrate.py --groups 1 --destination 2

# Migrate Scheduled Tasks from endpoint 1 (SWP US-1) to endpoint 2 (SWP DE-1)
$ ./aio-migrate.py --scheduled-tasks 1 --destination 2
```

## How to Migrate from SWP to SWP

Migrating Vision One Server & Workload Protection to another instance of Vision One Server & Workload Protection:

> ***Example below assumes:***
>
> - Destination SWP is configured as ID 1
> - Source SWP is configured as ID 2

1. Create Computer Group structure in SWP: `./aio-migrate.py --groups 2 --destination 1`
2. Create Smart Folder structure in SWP: `./aio-migrate.py --folders 2 --destination 1`
3. Export required policies starting with the relevant root policy using `Export --> Export Selected to XML (For Import)...` in the source SWP.
4. Import the `.xml` file to the destination SWP.
5. ***TODO:*** Reactivate the Agents to the destination SWP.
6. Merge the Scheduled Tasks: `./aio-migrate.py --scheduled-tasks 2 --destination 1`
7. Merge the Event-based Tasks: `./aio-migrate.py --event-based-tasks 2 --destination 1`

> ***Notes:***
> - Contacts with the predefined role of 'Auditor' are automatically created if they do not exist in the target environment.
> - Administrators will not be migrated since the API-Key of SWP does not have the necessary permissions to create Administrators.

## How to Migrate from DS to SWP

Migrating Deep Security to Vision One Server & Workload Protection:

> ***Example below assumes:***
>
> - Destination SWP is configured as ID 1
> - Source DS is configured as ID 2

1. Create Computer Group structure in SWP: `./aio-migrate.py --groups 2 --destination 1`
2. Create Smart Folder structure in SWP: `./aio-migrate.py --folders 2 --destination 1`
3. Migrate the Common Objects, Policies, and Computers with the official Migration Tool
   1. The migrated policies will get a suffix generated (e.g. ` (2024-11-14T16:26:36Z 10.0.0.84)`). Use this suffix as the `--policysuffix` for `scheduled-tasks.py` in the next step.
4. Merge the Scheduled Tasks: `./aio-migrate.py --scheduled-tasks 2 --destination 1 --policysuffix " (2024-11-14T16:26:36Z 10.0.0.84)"`
4. Merge the Event-based Tasks: `./aio-migrate.py --event-based-tasks 2 --destination 1 --policysuffix " (2024-11-14T16:26:36Z 10.0.0.84)"`

> ***Notes:***
> - Contacts with the predefined role of 'Auditor' are automatically created if they do not exist in the target environment.
> - Administrators will not be migrated since the API-Key of SWP does not have the necessary permissions to create Administrators.

## Deprecatd:

Chapter only relevant for `groups-and-folders` and `scheduled-tasks`.

### Preparation of the Scripts

- Set environment variable `API_KEY_SWP` with the API key of the
  Server & Workload Security instance to use.
- Set environment variable `API_KEY_DS` with the API key of the
  Deep Security instance to use.
- Adapt the constants in between
  `# HERE`
  and
  `# /HERE`
  within the scripts to your requirements.
  ```sh
  # HERE
  REGION_SWP = "us-1."  # Examples: de-1. sg-1.
  API_BASE_URL_DS = "https://3.76.217.110:4119/api/"
  # /HERE
  ```

Change to the directory of the desired script and install dependencies:

```sh
cd groups-and-folders

python3 -m venv venv && source venv/bin/activate

pip install -r requirements.txt
```

### Groups and Folders

The Python script `groups-and-folders.py` implements for following functionality:

- List Computer Groups in DS and SWP
- List Smart Folders in DS and SWP
- Merge Computer Group structure from DS with SWP and vice versa
- Merge Smart Folders structure from DS with SWP and vice versa

***Options and Examples***

```sh
usage: python3 groups-and-folders.py [-h] [--listgroups TYPE] [--mergegroups TYPE] [--listfolders TYPE] [--mergefolders TYPE]

List and merge Computer Groups and Smart Folders in between DS and SWP

options:
  -h, --help           show this help message and exit
  --listgroups TYPE    list computer groups (TYPE=ds|swp)
  --mergegroups TYPE   merge computer groups from given source (TYPE=ds|swp)
  --listfolders TYPE   list smart folders (TYPE=ds|swp)
  --mergefolders TYPE  list smart folders from given source (TYPE=ds|swp)

Examples:
--------------------------------
# Merge Computer Groups from DS with SWP
$ ./groups-and-folders.py --mergegroups ds

# List Smart Folders in SWP
$ ./groups-and-folders.py --listfolders swp
```

### Scheduled Tasks

The Python script `scheduled-tasks.py` implements for following functionality:

- List Scheduled Tasks in DS and SWP
- Merge Scheduled Tasks from DS with SWP and vice versa

***Options and Examples***

```sh
usage: python3 scheduled-tasks.py [-h] [--listtasks TYPE] [--mergetasks TYPE] [--policysuffix POLICYSUFFIX] [--taskprefix TASKPREFIX]

List and merge Scheduled Tasks in between DS and SWP

options:
  -h, --help            show this help message and exit
  --listtasks TYPE      list scheduled tasks (TYPE=ds|swp)
  --mergetasks TYPE     merge scheduled tasks from given source (TYPE=ds|swp)
  --policysuffix POLICYSUFFIX
                        Optional policy name suffix.
  --taskprefix TASKPREFIX
                        Optional task name prefix.

Examples:
--------------------------------
# Merge Scheduled Tasks from DS with SWP
$ ./scheduled-tasks.py --mergetasks ds --policysuffix " (2024-11-14T16:26:36Z 10.0.0.84)" --taskprefix "DS"

# List Scheduled Tasks in SWP
$ ./scheduled-tasks.py --listtasks swp
```

## Support

This is an Open Source community project. Project contributors may be able to help, depending on their time and availability. Please be specific about what you're trying to do, your system, and steps to reproduce the problem.

For bug reports or feature requests, please [open an issue](../../issues). You are welcome to [contribute](#contribute).

Official support from Trend Micro is not available. Individual contributors may be Trend Micro employees, but are not official support.

## Contribute

I do accept contributions from the community. To submit changes:

1. Fork this repository.
2. Create a new feature branch.
3. Make your changes.
4. Submit a pull request with an explanation of your changes or additions.

I will review and work with you to release the code.
