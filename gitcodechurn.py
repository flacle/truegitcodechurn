'''
Authors: 
- Francis Laclé
- Jonathan Guerne
License: MIT
Version: 1.2.1

Script to compute "true" code churn of a Git repository.

Code churn has several definitions, the one that to me provides the
most value as a metric is:

"Code churn is when an engineer rewrites their own code in a short time period."

Reference: https://blog.gitprime.com/why-code-churn-matters/

This lightweight script looks at commits per author for a given date range on
the default branch. For each commit it bookkeeps the files that were changed
along with the lines of code (LOC) for each file. LOC are kept in a sparse
structure and changes per LOC are taken into account as the program loops. When
a change to the same LOC is detected it updates this separately to bookkeep the
true code churn.

Result is a print with aggregated contribution and churn per author for a
given time period.

Tested with Python version 3.5.3 and Git version 2.20.1

'''

import subprocess
import shlex
import os
import argparse
import datetime
from time import strptime

def main():
    parser = argparse.ArgumentParser(
        description = 'Compute true git code churn to understand tech debt.',
        usage       = 'python [*/]gitcodechurn.py after="YYYY[-MM[-DD]]" before="YYYY[-MM[-DD]]" author="flacle" dir="[*/]path" [-exdir="[*/]path"]',
        epilog      = 'Feel free to fork at or contribute on: https://github.com/flacle/truegitcodechurn'
    )
    parser.add_argument(
        'after',
        type = str,
        help = 'search after a certain date, in YYYY[-MM[-DD]] format'
    )
    parser.add_argument(
        'before',
        type = str,
        help = 'search before a certain date, in YYYY[-MM[-DD]] format'
    )
    parser.add_argument(
        '-start-commit',
        type = str,
        help = 'search from a certain commit, in short SHA format'
    )
    parser.add_argument(
        '-end-commit',
        type = str,
        help = 'search to a certain commit, in short SHA format'
    )
    parser.add_argument(
        'author',
        type = str,
        help = 'an author (non-committer), leave blank to scope all authors'
    )
    parser.add_argument(
        'dir',
        type = dir_path,
        default = '',
        help = 'the Git repository root directory to be included'
    )
    parser.add_argument(
        '-exdir',
        metavar='',
        type = str,
        default = '',
        help = 'the Git repository subdirectory to be excluded'
    )
    args = parser.parse_args()

    after  = args.after
    before = args.before
    start_commit = args.start_commit
    end_commit = args.end_commit
    author = args.author
    dir    = args.dir
    # exdir is optional
    exdir  = args.exdir

    # for the positionals we remove the prefixes
    # TODO not sure why this is happening
    after   = remove_prefix(after, 'after=')
    before  = remove_prefix(before, 'before=')
    author  = remove_prefix(author, 'author=')
    # dir is already handled in dir_path()

    # retrive start and end commit date from given commit hashes
    start_commit_date = get_commit_timestamp(start_commit, dir) if start_commit else None
    end_commit_date = get_commit_timestamp(end_commit, dir) if end_commit else None

    # sort commit date if necessary
    if start_commit_date and end_commit_date:
        start_commit_date, end_commit_date = sorted([start_commit_date, end_commit_date])

    # return specified commit if it is the same for the start and end value
    # otherwise look for commits in between
    if start_commit is not None and start_commit == end_commit:
        commits = [start_commit]
    else :
        commits = get_commits(end_commit_date or before, start_commit_date or after, author, dir)

    # structured like this: files -> LOC
    files = {}

    contribution = 0
    churn = 0

    for commit in commits:
        [files, contribution, churn] = get_loc(
            commit,
            dir,
            files,
            contribution,
            churn,
            exdir
        )

    # if author is empty then print a unique list of authors
    if len(author.strip()) == 0:
        authors = set(get_commits(end_commit or before, start_commit or after, author, dir, '%an')).__str__()
        authors = authors.replace('{', '').replace('}', '').replace("'","")
        print('authors: \t', authors)
    else:
        print('author: \t', author)
    print('contribution: \t', contribution)
    print('churn: \t\t', -churn)
    # print files in case more granular results are needed
    #print('files: ', files)

def get_commit_timestamp(commit_hash, dir):

    # if the given hash is shorter than required it generate an error
    if len(commit_hash) < 7:
        raise argparse.ArgumentTypeError(commit_hash + " is not a valid commit hash.")

    # take short hash if commit hash is too long
    commit_hash = commit_hash[:7]

    #look for log with corresponding hash
    command = 'git show ' + commit_hash
    results = get_proc_out(command, dir).splitlines()

    # search the date and remove unwanted prefix and suffix
    date_raw = [r for r in results if r.startswith("Date:")][0][5:-5].strip()

    # transform the raw_date into a time object. Use this object to output the date in YYYY-MM-DD HH:mm format
    date_object = strptime(date_raw)
    res = f"{date_object.tm_year:04d}-{date_object.tm_mon:02d}-{date_object.tm_mday:02d} "
    res += f"{date_object.tm_hour:02d}:{date_object.tm_min:02d}"

    return res

def get_loc(commit, dir, files, contribution, churn, exdir):
    # git show automatically excludes binary file changes
    command = 'git show --format= --unified=0 --no-prefix ' + commit
    if len(exdir) > 1:
        # https://stackoverflow.com/a/21079437
        command += ' -- . ":(exclude,icase)'+exdir+'"'
    results = get_proc_out(command, dir).splitlines()
    file = ''
    loc_changes = ''

    # loop through each row of output
    for result in results:
        new_file = is_new_file(result, file)
        if file != new_file:
            file = new_file
            if file not in files:
                files[file] = {}
        else:
            new_loc_changes = is_loc_change(result, loc_changes)
            if loc_changes != new_loc_changes:
                loc_changes = new_loc_changes
                locc = get_loc_change(loc_changes)
                for loc in locc:
                    if loc in files[file]:
                        files[file][loc] += locc[loc]
                        churn += abs(locc[loc])
                    else:
                        files[file][loc] = locc[loc]
                        contribution += abs(locc[loc])
            else:
                continue
    return [files, contribution, churn]

# arrives in a format such as -13 +27,5 (no commas mean 1 loc change)
# this is the chunk header where '-' is old and '+' is new
# it returns a dictionary where left are removals and right are additions
# if the same line got changed we subtract removals from additions
def get_loc_change(loc_changes):
    # removals
    left = loc_changes[:loc_changes.find(' ')]
    left_dec = 0
    if left.find(',') > 0:
        comma = left.find(',')
        left_dec = int(left[comma+1:])
        left = int(left[1:comma])
    else:
        left = int(left[1:])
        left_dec = 1

    # additions
    right = loc_changes[loc_changes.find(' ')+1:]
    right_dec = 0
    if right.find(',') > 0:
        comma = right.find(',')
        right_dec = int(right[comma+1:])
        right = int(right[1:comma])
    else:
        right = int(right[1:])
        right_dec = 1

    if left == right:
        return {left: (right_dec - left_dec)}
    else:
        return {left : left_dec, right: right_dec}

def is_loc_change(result, loc_changes):
    # search for loc changes (@@ ) and update loc_changes variable
    if result.startswith('@@'):
        loc_change = result[result.find(' ')+1:]
        loc_change = loc_change[:loc_change.find(' @@')]
        return loc_change
    else:
        return loc_changes

def is_new_file(result, file):
    # search for destination file (+++ ) and update file variable
    if result.startswith('+++'):
        return result[result.rfind(' ')+1:]
    else:
        return file

# use format='%an' to get a list of author names
def get_commits(before, after, author, dir, format='%h'):
    # note --no-merges flag (usually we coders do not overhaul contrib commits)
    # note --reverse flag to traverse history from past to present
    command = 'git log --author="'+author+'" --format="'+format+'" --no-abbrev '
    command += '--before="'+before+'" --after="'+after+'" --no-merges --reverse'
    return get_proc_out(command, dir).splitlines()

# issue #6: append to date if it's missing month or day values
def format_date(d):
    d = d[:-1] if d.endswith('-') else d
    if len(d) < 6:
            # after is interpreted as 'after the year YYYY'
            return d[0:4]+'-12-31'
    elif len(d) < 8:
        # here we need to check on which day a month ends
        dt = datetime.datetime.strptime(d, '%Y-%m')
        dt_day = get_month_last_day(dt)
        dt_month = '{:02d}'.format(dt.month).__str__()
        return d[0:4]+'-'+dt_month+'-'+dt_day
    else:
        dt = datetime.datetime.strptime(d, '%Y-%m-%d')
        dt_day = '{:02d}'.format(dt.day).__str__()
        dt_month = '{:02d}'.format(dt.month).__str__()
        return d[0:4]+'-'+dt_month+'-'+dt_day

# https://stackoverflow.com/a/43088
def get_month_last_day(date):
    if date.month == 12:
        return date.replace(day=31)
    ld = date.replace(month=date.month+1, day=1)-datetime.timedelta(days=1)
    return ld.day.__str__()

# not used but still could be of value in the future
def get_files(commit, dir):
    # this also works in case --no-merges flag is ommitted prior
    command = 'git show --numstat --pretty="" ' + commit
    results = get_proc_out(command, dir).splitlines()
    for i in range(len(results)):
        # remove the tabbed stats from --numstat
        results[i] = results[i][results[i].rfind('\t')+1:]
    return(results)

def get_proc_out(command, dir):
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=dir,
        shell=True
    )
    return process.communicate()[0].decode("utf-8")

# https://stackoverflow.com/a/54547257
def dir_path(path):
    path = remove_prefix(path, 'dir=')
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(path + " is not a valid path.")

#https://stackoverflow.com/a/16891418
def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text  # or whatever

if __name__ == '__main__':
    main()
