import json
import re
import csv
import subprocess
import dateutil.parser
import pytz
import argparse
from libmozdata import patchanalysis

import get_bugs

def get_date(dt):
    d = dateutil.parser.parse(dt)
    if d.tzinfo is None or d.tzinfo.utcoffset(d) is None:
        return pytz.utc.localize(d)
    return d.astimezone(pytz.utc)

# Execute a shell command
def shellCommand(command_str):
    cmd = subprocess.Popen(command_str, shell=True, stdout=subprocess.PIPE)
    cmd_out, cmd_err = cmd.communicate()
    return cmd_out

# Load the mapping between bugs and their fixing commits
def loadBugCommitMapping(filename):
    bug_commit_mapping = dict()
    with open(filename, 'r') as f:
        raw_data = json.load(f)
        for stage in raw_data:
            for mapping in raw_data[stage]:
                bug_id = str(mapping['bug_id'])
                commits = set(mapping['commits'])
                if len(commits):
                    bug_commit_mapping[bug_id] = commits
    return bug_commit_mapping

# Load commit date.
# Generate the file via this command: hg log --template '{node|short}\t{date|isodate}\n' > commit_date.csv)
def loadCommitDate(filename):
    commit_date_dict = dict()
    with open(filename, 'r') as f:
        csvreader = csv.reader(f, delimiter='\t')
        for line in csvreader:
            commit_date_dict[line[0]] = line[1]
    return commit_date_dict

def loadResults(filename):
    result_list = []
    with open(filename, 'r') as f:
        csvreader = csv.reader(f, delimiter=',')
        for line in csvreader:
            result_list.append([line[0], line[1]])
    return result_list[1:]
    
# Extract deleted line numbers for a commit
def changedLines(commit_id, file_path):
    deleted_delta_cnt = -1
    deleted_line_set = set()
    # request diff from the Hg repository
    diff_res = shellCommand(HG_BIN + ' -R %s diff -c %s %s' %(HG_REPO_PATH,commit_id,file_path))
    # extract changed lines
    for line in diff_res.split('\n'):
        if re.match(r'@@[\+\-\,0-9\s]+@@', line):
            changed_range = re.findall(r'@@(.+)@@', line)[0].strip()
            deleted_range = changed_range.split(' ')[0][1:].split(',')
            deleted_delta_cnt = 0
        elif deleted_delta_cnt >= 0:
            if re.search(r'^\-', line):
                deleted_line_set.add(int(deleted_range[0]) + deleted_delta_cnt)
                deleted_delta_cnt += 1
            else:
                deleted_delta_cnt += 1
    return deleted_line_set
    
#   Detect changed revision numbers for each bug fix
def filterCandidate(annotate_res, deleted_line_set):
    candidate_set = set()
    block_comment = False
    for line in annotate_res.split('\n'):
        if len(line):
            elems = line.split(':', 2)
            commit = elems[0].strip()
            line_num = elems[1].strip()
            changed_code = elems[2].strip()
            #   filter out the meaningless lines (i.e., lines without letters), and comment lines
            if len(changed_code) > 0 and re.search(r'[a-zA-Z]', changed_code):                
                if block_comment:
                    if '*/' in changed_code:
                        block_comment = False
                        valid_code = re.sub(r'.+\*\/', '', changed_code)
                elif ('/*' in changed_code) and ('*/' not in changed_code):
                    block_comment = True
                    valid_code = re.sub(r'\/\*.+', '', changed_code)
                else:
                    valid_code = re.sub(r'\/\*.+\*\/', '', re.sub(r'\/\/.+', '', changed_code))
                #   take only the valid lines as bug-inducing candidates
                if len(valid_code) > 0 and re.search(r'[a-zA-Z]', valid_code):
                    #print rev_num, '\t', changed_code
                    if int(line_num) in deleted_line_set:
                        candidate_set.add(commit)
    return candidate_set    

# Perform Hg annotate command
def hgAnnotate(commit_id, file_list):
    candidate_set = dict()
    for f in file_list:
        if re.search(r'(c|cpp|cc|cxx|h|hpp|hxx)$', f):
            file_path = HG_REPO_PATH + f
            deleted_line_set = changedLines(commit_id, file_path)
            # blame the parent revision, and select the "-" lines' corresponding revision numbers
            parent_commit = commit_id + '^'
            blame_res = shellCommand(HG_BIN + ' -R %s annotate -r %s %s -c -l -w -b -B' %(HG_REPO_PATH,parent_commit,file_path))  
            candidate_set = filterCandidate(blame_res, deleted_line_set)
    return candidate_set

# Identify crash-inducing commit for each crash-related bug
def crashInducing(bug_open_date, bug_fix_commits, commit_date_dict):
    bug_inducing_commits = set()
    for commit_id in bug_fix_commits:
        # extract a commit's modified and deleted files, and its parent sha
        cmd_out = shellCommand(HG_BIN + ' -R %s log -r %s --template "{file_mods}\n{file_dels}"' %(HG_REPO_PATH,commit_id))
        items = cmd_out.split('\n')
        changed_files = set(items[0].split(' ') + items[1].split(' '))
        # apply SZZ algorithm
        candidate_set = hgAnnotate(commit_id, changed_files)
        # candidate must be committed before the bug's open date
        if len(candidate_set):
            for candidate_commit in candidate_set:
                candidate_date = get_date(commit_date_dict[candidate_commit])
                if candidate_date < bug_open_date:
                    bug_inducing_commits.add(candidate_commit)
    return bug_inducing_commits

# Output results to csv
def outputResults(result_list, outputfile):
    import pandas as pd
    df = pd.DataFrame(result_list, columns=['bug_id', 'bug_inducing_commits'])
    df.to_csv(outputfile, index=False)
    return

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Bug-inducing analysis')
    parser.add_argument('repo', action='store', help='the path to the repository')
    parser.add_argument('-t', '--type', action='store', default='all_bugs', choices=['all_bugs', 'uplift_bugs'])
    parser.add_argument('-m', '--mercurial-bin', action='store', default='hg', help='path to the \'hg\' binary')
    parser.add_argument('-d', '--debug', action='store_true', help='whether to perform a dry-run to debug problems')
    args = parser.parse_args()

    HG_REPO_PATH = args.repo
    HG_BIN = args.mercurial_bin

    if args.type == 'all_bugs':
        bugs = get_bugs.get_all_bugs()
    elif args.type == 'uplift_bugs':
        bugs = get_bugs.get_uplift_bugs()

    commit_date_dict = loadCommitDate('commit_date.csv')

    try:
        with open(args.type + '/bug_inducing_commits.json', 'r') as f:
            results = json.load(f)
    except:
        results = dict()

    result_ids = set([int(bid) for bid in results.keys()])
    remaining_bugs = [bug for bug in bugs if int(bug['id']) not in result_ids]
    print(str(len(remaining_bugs)) + ' bugs left to analyze.')

    i = len(results)
    for bug in remaining_bugs:
        i += 1
        if i > 5 and args.debug:
            break

        print(str(i) + ' out of ' + str(len(bugs)) + ': ' + str(bug['id']))

        bug_open_date = get_date(bug['creation_time'])
        if bug_open_date:
            bug_fix_commits, _ = patchanalysis.get_commits_for_bug(bug)
            bug_inducing_commits = crashInducing(bug_open_date, bug_fix_commits, commit_date_dict)
            # add bug_inducing commits to the result list
            if len(bug_inducing_commits):
                print bug_inducing_commits
            results[bug['id']] = list(bug_inducing_commits)

        if not args.debug:
            with open(args.type + '/bug_inducing_commits.json', 'w') as f:
                json.dump(results, f)

    if not args.debug:
        result_list = [[bug_id, '^'.join(bug_inducing_commits)] for bug_id, bug_inducing_commits in results.items()]
        outputResults(result_list, args.type + '/bug_inducing_commits.csv')
