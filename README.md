# Deep Security to Server & Workload Protection Migration Tools

This repo hosts tools to support a migration from Deep Security to Vision One Server & Workload Protection. Currently there is only one, but more are likely to come.

Abbreviations used:

- DS: Deep Security
- SWP: Vision One Server & Workload Protection

Get the code:

```sh
git clone https://github.com/mawinkler/ds-swp-migration-tools.git
cd ds-swp-migration-tools
```

## How the Scripts Support the Migration Workflow

Migrating Deep Security to Vision One Server & Workload Protection:

1. Create Computer Group structure in SWP: `groups-and-folders.py --mergegroups ds`
2. Create Smart Folder structure in SWP: `groups-and-folders.py --mergefolders ds`
3. Migrate the Common Objects, Policies, and Computers with the official Migration Tool
   1. The migrated policies will get a suffix generated (e.g. ` (2024-11-14T16:26:36Z 10.0.0.84)`). Use this suffix as the `--policysuffix` for `scheduled-tasks.py` in the next step.
4. Merge the Scheduled Tasks: `scheduled-tasks.py --mergetasks ds --policysuffix " (2024-11-14T16:26:36Z 10.0.0.84)"`

> ***Notes:***
> 
> TODO: Contacts are automatically created if not existent and they have a valid email address.
> 
> Administrators will not be migrated since the API-Key of SWP does not have the necessary permissions to create Administrators.

## Preparation of the Scripts

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

## Groups and Folders

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

## Scheduled Tasks (ALPHA)

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
