import re, csv, pytz, json, subprocess
from dateutil import parser
import pandas as pd
import get_bugs
from libmozdata import patchanalysis

# Execute a shell command
def shellCommand(command_str):
    cmd =subprocess.Popen(command_str.split(' '), stdout=subprocess.PIPE)
    cmd_out, cmd_err = cmd.communicate()
    return cmd_out

def loadReleaseDate():
    print 'Loading Relase date ...'
    rel_date_list = list()
    rel_list = list()
    with open('complexity_sna/data/release2commit.csv') as f:
        csvreader = csv.reader(f)
        for row in csvreader:
            rel_num = row[0]
            rel_date = re.sub(r'[^0-9]', '', row[2])
            rel_date_list.append([rel_date, rel_num])
            rel_list.append(rel_num)
    return rel_date_list, list(reversed(rel_list))

def loadCommitDate():
    print 'Loading commit date ...'
    commit_date_dict = dict()
    with open('commit_date.csv') as f:
        csvreader = csv.reader(f, delimiter='\t')
        for row in csvreader:
            commit_id = row[0]
            raw_time = row[1]
            datetime_obj = parser.parse(raw_time)
            time_str = datetime_obj.astimezone(pytz.utc).strftime('%Y%m%d')
            commit_date_dict[commit_id] = time_str
    return commit_date_dict

def correspondingRelease(commit_id, commit_date_dict, rel_date_list):
    if commit_id in commit_date_dict:
        commit_date = commit_date_dict[commit_id]
    else:
        for key in commit_date_dict:
            if commit_id in key:
                commit_date = commit_date_dict[key]
    for item in rel_date_list:
        if commit_date >= item[0]:
            return item[1]
    return rel_date_list[-1][1]

def removePrefix(path):
    return re.sub(r'^[\/\.]+', '', path)

def loadMetrics4Releases(category, release_list):
    rel_metric_dict = dict()
    metric_names = None
    for rel in release_list:
        metric_dict = dict()
        metric_file = 'complexity_sna/code_metrics/%s-%s.csv' %(category, rel.replace('.', '_'))
        with open(metric_file, 'r') as f:
            csvreader = csv.reader(f)
            metric_names = next(csvreader, None)[1:]
            for line in csvreader:
                key = removePrefix(line[0])
                metric_dict[key] = line[1:]
            rel_metric_dict[rel] = metric_dict
    return rel_metric_dict, metric_names

def extractSourceCodeMetrics(rel_date_list, rel_list, commit_date_dict, category):
    # load metrics
    rel_metric_dict, metric_names = loadMetrics4Releases(category, rel_list)
    # map and compute metric values
    result_list = list()
    i = 0

    bugs = get_bugs.get_all()

    for bug in bugs:
        if DEBUG and i > 5:
            break

        bug_id = bug['id']
        commits, _ = patchanalysis.get_commits_for_bug(bug)

        print bug_id

        # extract metrics
        raw_list = list()
        metric_list = list()
        for commit_id in commits:
            i += 1
            if DEBUG:
                print ' ', commit_id
            # corresponding (prior) release of a commit
            rel_num = correspondingRelease(commit_id, commit_date_dict, rel_date_list)
            # changed files in a commit
            shell_res = shellCommand('hg -R %s log -r %s --template {files}\t{diffstat}' %(HG_REPO_PATH, commit_id)).split('\t')
            raw_changed_files = shell_res[0]
            cpp_changed_files = re.findall(r'(\S+\.(?:c|cpp|cc|cxx|h|hpp|hxx)\b)', raw_changed_files)
            # map file/node to metrics
            for a_file in cpp_changed_files:
                metric_dict = rel_metric_dict[rel_num]
                for node in metric_dict:
                    if node in a_file:
                        metrics = metric_dict[node]
                        raw_list.append(metrics)
        # compute average/sum value for a specific attachment
        if len(raw_list):
            df = pd.DataFrame(raw_list, columns=metric_names).apply(pd.to_numeric)
            for metric_name in metric_names:
                metric_list.append(round(df[metric_name].mean(), 2))
            result_list.append([bug_id] + metric_list)
        else:
            result_list.append([bug_id] + [0]*len(metric_names))
    
    return pd.DataFrame(result_list, columns=['bug_id']+metric_names)

if __name__ == '__main__':
    DEBUG = False
    HG_REPO_PATH = '../firefox/'
    # load data
    rel_date_list, rel_list = loadReleaseDate()
    commit_date_dict = loadCommitDate()
    # extract metrics
    df_complexity = extractSourceCodeMetrics(rel_date_list, rel_list, commit_date_dict, 'complexity')
    df_sna = extractSourceCodeMetrics(rel_date_list, rel_list, commit_date_dict, 'sna')
    df_code = pd.merge(df_complexity, df_sna, on='bug_id')
    df_code.to_csv('independent_metrics/src_code_metrics.csv', index=False)
    if DEBUG:
        print df_code
    
