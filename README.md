# True Git Code Churn

![GitHub release version](https://img.shields.io/github/v/release/flacle/truegitcodechurn.svg?sort=semver)

A Python script to compute "true" code churn of a Git repository. Useful for software teams to openly help manage technical debt.

Code churn has several definitions, the one that to me provides the most value as a metric is:

> "Code churn is when an engineer rewrites their own code in a short period of time."

*Reference: https://www.pluralsight.com/blog/teams/why-code-churn-matters*

Solutions that I've found online looked at changes to files irrespective whether these are new changes or edits to existing lines of code (LOC) within existing files. Hence this solution that segments line-of-code edits (churn) with new code changes (contribution).

*Tested with Python version 3.5.3 and Git version 2.20.1*

## How it works

This lightweight script looks at commits per author for a given date range on the **current branch**. For each commit it bookkeeps the files that were changed along with the LOC for each file. LOC are kept in a sparse structure and changes per LOC are taken into account as the program loops. When a change to the same LOC is detected it updates this separately to bookkeep the true code churn.
Result is a print with aggregated contribution and churn per author for a given period in time.

***Note:*** This includes the `--no-merges` flag as it assumes that merge commits with or without merge conflicts are not indicative of churn.

## Usage

### Positional (required) arguments

- **after**        after a certain date, in YYYY[-MM[-DD]] format
- **before**     before a certain date, in YYYY[-MM[-DD]] format
- **author**     author string (not a committer), leave blank to scope all authors
- **dir**            include Git repository directory

### Optional arguments

- **-h, --h, --help**    show this help message and exit
- **-exdir**                   exclude Git repository subdirectory
-- **--show-file-data**        display line count changes per file

## Usage Example 1

```bash
python ./gitcodechurn.py after="2018-11-29" before="2019-03-01" author="an author" dir="/Users/myname/myrepo" -exdir="excluded-directory"
```

## Output 1

```bash
author:       an author
contribution: 844
churn:        -28
```

## Usage Example 2

```bash
python ./gitcodechurn.py after="2018-11-29" before="2019-03-01" author="" dir="/Users/myname/myrepo" -exdir="excluded-directory"
```

## Output 2

```bash
authors:      author1, author2, author3
contribution: 4423
churn:        -543
```

## Usage Example 3

```bash
python ./gitcodechurn.py after="2018-11-29" before="2021-11-05" author="flacle" dir="/Users/myname/myrepo" --show-file-data
```

## Output 3

```bash
author:          flacle
contribution:    337
churn:           -19
-------------------------------------------------------------------------------
            FILE NAME             |  LINE #  |  ADDED   | REMOVED  
-------------------------------------------------------------------------------
         gitcodechurn.py          |    1     |   190    |    0     
-------------------------------------------------------------------------------
         gitcodechurn.py          |    2     |    4     |    0     
-------------------------------------------------------------------------------
         gitcodechurn.py          |    37    |    2     |    0     
-------------------------------------------------------------------------------
         gitcodechurn.py          |    40    |    0     |    1     
-------------------------------------------------------------------------------
         gitcodechurn.py          |    42    |    1     |    0     
-------------------------------------------------------------------------------
         gitcodechurn.py          |    45    |    0     |    1     
-------------------------------------------------------------------------------
         gitcodechurn.py          |    47    |    1     |    0     
-------------------------------------------------------------------------------
         gitcodechurn.py          |    50    |    0     |    1     
-------------------------------------------------------------------------------
         gitcodechurn.py          |    52    |    1     |    0     
-------------------------------------------------------------------------------
         gitcodechurn.py          |    55    |    0     |    1     
-------------------------------------------------------------------------------
         gitcodechurn.py          |    57    |    8     |    1     
-------------------------------------------------------------------------------
         gitcodechurn.py          |    66    |    2     |    0     
-------------------------------------------------------------------------------
         gitcodechurn.py          |    62    |    0     |    1     
...
-------------------------------------------------------------------------------
         gitcodechurn.py          |   200    |    1     |    0     
-------------------------------------------------------------------------------
            README.md             |    12    |    2     |    0     
-------------------------------------------------------------------------------
            README.md             |    16    |    0     |    1     
-------------------------------------------------------------------------------
            README.md             |    18    |    1     |    0     
-------------------------------------------------------------------------------
            README.md             |    21    |    11    |    0     
-------------------------------------------------------------------------------
            README.md             |    20    |    0     |    1     
-------------------------------------------------------------------------------
            README.md             |    33    |    1     |    0     
-------------------------------------------------------------------------------
            README.md             |    22    |    0     |    1     
-------------------------------------------------------------------------------
            README.md             |    35    |    1     |    0     
-------------------------------------------------------------------------------
            README.md             |    24    |    0     |    2     
-------------------------------------------------------------------------------
            README.md             |    37    |    3     |    0     
-------------------------------------------------------------------------------
            README.md             |    41    |    12    |    0     
```

Outputs of Usage Example 1 can be used as part of a pipeline that generates bar charts for reports:
![contribution vs churn example chart](/chart.png)

## How to contribute

At this time, the code is organized into a script which can be located at `gitcodechurn.py`. There is [an open issue](https://github.com/flacle/truegitcodechurn/issues/9) to conver this repository
into a more formal Object Oriented structure.

For now the code is located in `gitcodechurn.py` and the tests are located in `test_gitcodechurn.py`. To test, kindly ensure `pytest` and `pytest-mock` are installed. Then, in project root run

```bash
pytest
```
