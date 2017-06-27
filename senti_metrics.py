from __future__ import division
import json, re, subprocess, os, string
import get_bugs
import pandas as pd

# Execute a shell command
def shellCommand(command_str):
    cmd = subprocess.Popen(command_str, shell=True, stdout=subprocess.PIPE)
    cmd_out, cmd_err = cmd.communicate()
    return cmd_out

def loadPeopleList(file_name):
    people_list = list()
    with open(file_name) as f:
        for line in f.read().split():
            if len(line):
                people_list.append(line)
    return people_list

def removeStopWords(line):
    stop_words = ['default', 'debug', 'bug', 'error', 'issue', 'regression', 'failure', 'fail'\
                    'leak', 'crash']
    for sw in stop_words:
        line = re.sub(sw, '', line, re.IGNORECASE)
    return line

def extractSentiment(comment_words):
    SENTIPATH = '/home/leanx/bin/SentiStrength'
    current_dir = os.getcwd()
    # use SentiStrength
    os.chdir(SENTIPATH)
    senti_res = shellCommand('./SentiRun "%s"' %comment_words).strip()
    os.chdir(current_dir)
    return senti_res

def sentimentInText(comment_text):
    comment_words = list()
    try:
        for line in comment_text.split('\n'):
            if (# line should not be blank 
                len(line.strip()) and \
                # ignore referred text
                not line.startswith('>') and \
                # ignore "in reply to ..."
                not re.search(r'In reply to .+? (from comment \#[0-9]+)?', line) and \
                # ignore hyperlinksr
                not re.search(r'https?://[^\s<>"]+|www\.[^\s<>"]+', line) \
                ):
                # remove punctuation
                line = line.encode('utf-8').translate(None, string.punctuation.replace('\'', ''))
                # ignore bug report stop words
                line = removeStopWords(line)
                # remove redundant space
                line = re.sub('\s+', ' ', line)
                # concatenate all lines in a comment
                comment_words.append(line)
        extracted_comment = '\n'.join(comment_words)
        if len(extracted_comment):
#            print extracted_comment
            return extractSentiment(extracted_comment)
    except:
            print 'Unparsable message!'
    return '1 -1 0'

def sentiMetrics(commit_list):
    pos_list, neg_list, overall_list = list(), list(), list()
    module_owner_pos, module_owner_neg = [0], [0]
    rel_manager_pos, rel_manager_neg = [0], [0]
    for a_comment in commit_list:
        comment_text = a_comment['text']
        commenter = a_comment['author']
        comment_time = a_comment['time']
        senti_res = sentimentInText(comment_text).split(' ')
        pos_senti = int(senti_res[0])
        neg_senti = int(senti_res[1])
        pos_list.append(pos_senti)
        neg_list.append(neg_senti)
        overall_list.append(int(senti_res[2]))
        if commenter in module_owners:
            module_owner_pos.append(pos_senti)
            module_owner_neg.append(neg_senti)
        if commenter in rel_managers:
            rel_manager_pos.append(pos_senti)
            rel_manager_neg.append(neg_senti)
    max_pos = max(pos_list)
    min_neg = min(neg_list)
    overall = sum(pos_list+neg_list)
    return [max_pos, min_neg, overall, max(module_owner_pos), min(module_owner_neg), max(rel_manager_pos), min(rel_manager_neg)]

if __name__ == '__main__':
    DEBUG = False
    rel_managers = loadPeopleList('people_list/release_managers.txt')
    module_owners = loadPeopleList('people_list/module_owners.txt')
    
    print 'Loading bug reports ...'
    all_bugs = get_bugs.get_all()
    if DEBUG:
        bug_list = all_bugs[:10]
    else:
        bug_list = all_bugs
    total_len = len(bug_list)
    
    print 'Extracting metrics ...'
    output_list = list()
    i = 1
    for bug_item in bug_list:
        bug_id = bug_item['id']
        print '%s %.1f%%' %(bug_id, i/total_len*100)
        senti_metrics = sentiMetrics(bug_item['comments'])
        output_list.append([bug_id] + senti_metrics)
        shellCommand('sudo sysctl -w vm.drop_caches=3')
        i += 1
    df = pd.DataFrame(output_list, columns=['bug_id', 'max_pos', 'min_neg', 'overall', 'owner_pos', 'owner_neg', 'manager_pos', 'manager_neg'])
    df.to_csv('metrics/senti_metrics.csv', index=False)
    
    if DEBUG:
        print df
    
    print 'Done.'
