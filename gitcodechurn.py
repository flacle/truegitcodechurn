'''
Author: Francis Laclé
License: MIT
Version: 0.1

Script to compute "true" code churn of a Git repository.

Code churn has several definitions, the one that to me provides the
most value as a metric is:

"Code churn is when an engineer
rewrites their own code in a short period of time."

Reference: https://blog.gitprime.com/why-code-churn-matters/

This script looks at a range of commits per author. For each commit it
book-keeps the files that were changed along with the lines of code (LOC)
for each file. LOC are kept in a sparse structure and changes per LOC are taken
into account as the program loops. When a change to the same LOC is detected it
updates this separately to bookkeep the true code churn.

Result is a print with aggregated contribution and churn per author for a
given time period.

Tested with Python version 3.5.3 and Git version 2.20.1

'''

import subprocess
import shlex
import os
import argparse
import datetime

def main():
    parser = argparse.ArgumentParser(
        description = 'Compute true git code churn to understand tech debt.',
        usage       = 'python [*/]gitcodechurn.py before=YYY-MM-DD after=YYYY-MM-DD dir=[*/]path [-exdir=[*/]path] [-h]',
        epilog      = 'Feel free to fork at or contribute on: https://github.com/flacle/truegitcodechurn'
    )
    parser.add_argument(
        'before',
        type = str,
        help = 'before a certain date, in YYYY-MM-DD format'
    )
    parser.add_argument(
        'after',
        type = str,
        help = 'after a certain date, in YYYY-MM-DD format'
    )
    parser.add_argument(
        'author',
        type = str,
        help = 'author string (not committer)'
    )
    parser.add_argument(
        'dir',
        type = dir_path,
        default = '',
        help = 'include Git repository directory'
    )
    parser.add_argument(
        '-exdir',
        metavar='',
        type = str,
        default = '',
        help = 'exclude Git repository subdirectory'
    )
    args = parser.parse_args()

    before = args.before
    after  = args.after
    author = args.author
    dir    = args.dir
    # exdir is optional
    exdir  = args.exdir

    # for the positionals we remove the prefixes
    # TODO not sure why this is happening
    before  = remove_prefix(before, 'before=')
    after   = remove_prefix(after, 'after=')
    author  = remove_prefix(author, 'author=')
    # dir is already handled in dir_path()

    commits = get_commits(before, after, author, dir)

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

    print('contribution: ', contribution)
    print('churn: ', -churn)
    # print files in case more granular results are needed
    #print('files: ', files)

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

# arrives in a format such as -13 +27,5 (no decimals == 1 loc change)
# returns a dictionary where left are removals and right are additions
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

def get_commits(before, after, author, dir):
    # note --no-merges flag (usually we coders do not overhaul contrib commits)
    # note --reverse flag to traverse history from past to present
    command = 'git log --author="'+author+'" --format="%h" --no-abbrev '
    command += '--before="'+before+'" --after="'+after+'" --no-merges --reverse'
    return get_proc_out(command, dir).splitlines()

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
        raise argparse.ArgumentTypeError("Directory "+path+" is not a valid path.")

#https://stackoverflow.com/a/16891418
def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text  # or whatever

if __name__ == '__main__':
    main()
