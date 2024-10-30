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

## Groups and Folders

The Python script `groups-and-folders.py` implements for following functionality:

- List Computer Groups in DS and SWP
- List Smart Folders in DS and SWP
- Merge Computer Group structure from DS with SWP and vice versa
- Merge Smart Folders structure from DS with SWP and vice versa

***Requirements***

- Set environment variable API_KEY_SWP with the API key of the
  Server & Workload Security instance to use.
- Set environment variable API_KEY_DS with the API key of the
  Deep Security instance to use.
- Adapt the constants in between
  `# HERE`
  and
  `# /HERE`
  to your requirements

***Options***

```sh
-h, --help           show this help message and exit
--listgroups TYPE    list computer groups (TYPE=ds|swp)
--mergegroups TYPE   merge computer groups from given source (TYPE=ds|swp)
--listfolders TYPE   list smart folders (TYPE=ds|swp)
--mergefolders TYPE  list smart folders from given source (TYPE=ds|swp)
```

***Usage***

Change to the directory and install dependencies

```sh
cd groups-and-folders

python3 -m venv venv && source venv/bin/activate

pip install -r requirements.txt
```

Adapt two variables in `groups-and-folders.py` in lines 77 and 78:

```sh
# HERE
REGION_SWP = "us-1."  # Examples: eu-1. sg-1.
API_BASE_URL_DS = f"https://3.76.217.110:4119/api/"
# /HERE
```

Example usage:

```sh
# List current Smart Folders configured in DS
./groups-and-folders.py --listfolders ds

# List current Groups configured in DS
./groups-and-folders.py --listgroups ds

# List current Smart Folders configured in SWP
./groups-and-folders.py --listfolders swp

# List current Groups configured in SWP
./groups-and-folders.py --listgroups swp

# Merge current Groups in DS with Groups in SWP
# Existing Groups in SWP will not be overwritten, non-existing Groups will be merged into
# the hierarchy.
./groups-and-folders.py --mergegroups ds

# Merge current Smart Folders in DS with Smart Folders in SWP
# Existing Smart Folders in SWP will not be overwritten, non-existing Smart Folders will
# be merged into the hierarchy.
./groups-and-folders.py --mergefolders ds
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
