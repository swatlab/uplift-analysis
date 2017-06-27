# stdbuf --output=0 --error=0 python analyze_bugs.py all_bugs >> all_bugs/analyze_bugs.log 2>&1
# tail -f all_bugs/analyze_bugs.log

import os
import sys
import json
import argparse
import csv
import utils
import traceback
import multiprocessing
import subprocess
import time
from datetime import datetime

import get_bugs

author_cache = {
    'andrei.br92@gmail.com': ['aoprea@mozilla.com'],
    'bcheng.gt@gmail.com': ['brandon.cheng@protonmail.com'],
    'jwein@mozilla.com': ['jaws@mozilla.com'],
    'Olli.Pettay@helsinki.fi': ['bugs@pettay.fi'],
    'karlt+@karlt.net': ['karlt@mozbugz.karlt.net'],
    'mozilla@jorgk.com': ['jorgk@jorgk.com'],
    'Boris Zbarsky': ['bzbarsky@mit.edu'],
    'dholbert@cs.stanford.edu': ['dholbert@mozilla.com'],
    'nnethercote@mozilla.com': ['n.nethercote@gmail.com'],
    'billm@mozilla.com': ['wmccloskey@mozilla.com'],
    'romain.gauthier@monkeypatch.me': ['rgauthier@mozilla.com'],
    'dougt@dougt.org': ['doug.turner@gmail.com'],
    'seth@mozilla.com': ['seth.bugzilla@blackhail.net'],
    'dao@mozilla.com': ['dao+bmo@mozilla.com'],
    'bsmith@mozilla.com': ['brian@briansmith.org'],
    'georg.fritzsche@googlemail.com': ['gfritzsche@mozilla.com'],
    'kevina@gnu.org': ['kevin.bugzilla@atkinson.dhs.org', 'kevin.firefox.bugzilla@atkinson.dhs.org'],
    'Callek@gmail.com': ['bugspam.Callek@gmail.com'],
    'gavin@gavinsharp.com': ['gavin.sharp@gmail.com'],
    'jwalden@mit.edu': ['jeff.walden@gmail.com', 'jwalden+bmo@mit.edu', 'jwalden+fxhelp@mit.edu', 'jwalden+spammybugs@mit.edu'],
    'mikeperry': ['mikepery@fscked.org', 'mikeperry.unused@gmail.com', 'mikeperry@torproject.org'],
    'kgupta@mozilla.com': ['bugmail@mozilla.staktrace.com'],
    'Shane Caraveo': ['shanec@ActiveState.com', 'mixedpuppy@gmail.com', 'scaraveo@mozilla.com'],
    'scaraveo@mozilla.com': ['Shane Caraveo', 'shanec@ActiveState.com', 'mixedpuppy@gmail.com'],
    'justin.lebar@gmail.com': ['justin.lebar+bug@gmail.com'],
    'sylvestre@mozilla.com': ['sledru@mozilla.com'],
    'mrbkap@gmail.com': ['mrbkap@mozilla.com'],
    'archaeopteryx@coole-files.de': ['aryx.bugmail@gmx-topmail.de'],
    'matspal@gmail.com': ['mats@mozilla.com'],
    'neil@mozilla.com': ['enndeakin@gmail.com'],
    'mfinkle@mozilla.com': ['mark.finkle@gmail.com'],
    'dtownsend@oxymoronical.com': ['dtownsend@mozilla.com'],
    'robert@ocallahan.org': ['roc@ocallahan.org'],
    'andrei.eftimie@softvision.ro': ['andrei@eftimie.com'],
    'sriram@mozilla.com': ['sriram.mozilla@gmail.com'],
    'amccreight@mozilla.com': ['continuation@gmail.com'],
    'mcsmurf@mcsmurf.de': ['bugzilla@mcsmurf.de', 'bugzilla2@mcsmurf.de'],
    'sikeda@mozilla.com': ['sotaro.ikeda.g@gmail.com'],
    'quanxunzhen@gmail.com': ['xidorn+moz@upsuper.org'],
    'jones.chris.g@gmail.com': ['cjones.bugs@gmail.com', 'cjones@mozilla.com'],
    'kit@yakshaving.ninja': ['kit@mozilla.com', 'kitcambridge@mozilla.com', 'kcambridge@mozilla.com'],
    'kit@mozilla.com': ['kit@yakshaving.ninja', 'kitcambridge@mozilla.com', 'kcambridge@mozilla.com'],
    'kitcambridge@mozilla.com': ['kit@mozilla.com', 'kit@yakshaving.ninja', 'kcambridge@mozilla.com'],
    'kcambridge@mozilla.com': ['kit@mozilla.com', 'kitcambridge@mozilla.com', 'kit@yakshaving.ninja'],
    'aaronraimist@riseup.net': ['aaron@raim.ist'],
    'markus.nilsson@sonymobile.com': ['markus@hogpack.se'],
    'giles@mozilla.com': ['giles@thaumas.net', 'rillian@telus.net'],
    'tomcat@mozilla.com': ['tomcat_moz@yahoo.com', 'cbook@mozilla.com'],
    'joshmoz@gmail.com': ['jaas@kflag.net'],
    'benj@benj.me': ['bbouvier@mozilla.com'],
    'nsilva@mozilla.com': ['nical.bugzilla@gmail.com', 'nical.silva@gmail.com'],
    'olivier@olivieryiptong.com': ['oyiptong@mozilla.com'],
    'longster@gmail.com': ['jlong@mozilla.com'],
    'kats@mozilla.com': ['bugmail@mozilla.staktrace.com'],
    'paul@paul.cx': ['padenot@mozilla.com'],
    'senglehardt@mozilla.com': ['bugzilla@senglehardt.com'],
    'sworkman@mozilla.com': ['sjhworkman@gmail.com'],
    'jchan@mozilla.com': ['jyc@eqv.io'],
}

reviewer_cache = {
    'mt': 'martin.thomson@gmail.com',
    'j': 'j@mailb.org',
    'andrew': 'continuation@gmail.com',
}


def set_server():
    global patchanalysis

    server_ports_lock.acquire()
    next_server_port = server_ports.pop()
    server_ports.append(next_server_port + 1)
    server_ports_lock.release()

    stdout_server = open('server_' + str(next_server_port) + ".out", "a", buffering=0)

    subprocess.call('./serveHG.sh central ' + str(next_server_port) + ' &', shell=True, stdout=stdout_server, stderr=stdout_server)

    from libmozdata import config

    class MyConfig(config.ConfigIni):
        def __init__(self, path=None):
            super(MyConfig, self).__init__(path)

        def get(self, section, option, default=None, type=str):
            if section == 'Mercurial' and option == 'URL':
                print('http://127.0.0.1:' + str(next_server_port) + '/')
                return 'http://127.0.0.1:' + str(next_server_port) + '/'

            return super(MyConfig, self).get(section, option, default, type)

    config.set_config(MyConfig())

    from libmozdata import patchanalysis

    # HACKY! Wait for the server to start.
    time.sleep(5)


def analyze_bug(bug):
    sys.stdout = sys.stderr = open('analyze_bugs_' + str(os.getpid()) + ".out", "a", buffering=0)

    uplift_channels = utils.uplift_channels(bug)

    try:
        info = patchanalysis.bug_analysis(bug, author_cache=author_cache, reviewer_cache=reviewer_cache)

        # Translate sets into lists, as sets are not JSON-serializable.
        info['users']['authors'] = list(info['users']['authors'])
        info['users']['reviewers'] = list(info['users']['reviewers'])

        info['component'] = bug['component']
        info['channels'] = uplift_channels
        info['types'] = utils.get_bug_types(bug)

        for channel in uplift_channels:
            uplift_info = patchanalysis.uplift_info(bug, channel)
            del uplift_info['landings']
            info[channel + '_uplift_info'] = uplift_info
            # Transform timedelta objects to number of seconds (to make them JSON-serializable).
            info[channel + '_uplift_info']['landing_delta'] = int(uplift_info['landing_delta'].total_seconds())
            info[channel + '_uplift_info']['response_delta'] = int(uplift_info['response_delta'].total_seconds())
            info[channel + '_uplift_info']['release_delta'] = int(uplift_info['release_delta'].total_seconds())
            if uplift_info['uplift_accepted']:
                info[channel + '_uplift_info']['uplift_date'] = utils.get_uplift_date(bug, channel).strftime('%Y-%m-%d')
            uplift_reject_date = utils.get_uplift_reject_date(bug, channel)
            if uplift_reject_date is not None:
                info[channel + '_uplift_info']['uplift_reject_date'] = uplift_reject_date.strftime('%Y-%m-%d')

        analyzed_bugs_shared[str(bug['id'])] = info
    except Exception as e:
        print('Error with bug ' + str(bug['id']) + ': ' + str(e))
        traceback.print_exc()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Mine commit metrics')
    parser.add_argument('type', action='store', default='all_bugs', choices=['all_bugs', 'uplift_bugs'])
    args = parser.parse_args()

    DIR = args.type

    try:
        with open(os.path.join(DIR, 'analyzed_bugs.json'), 'r') as f:
            analyzed_bugs = json.load(f)
    except:
        analyzed_bugs = dict()

    bugs = get_bugs.get_all()
    remaining_bugs = [bug for bug in bugs if str(bug['id']) not in analyzed_bugs]

    manager = multiprocessing.Manager()
    analyzed_bugs_shared = manager.dict(analyzed_bugs)
    server_ports_lock = multiprocessing.Lock()
    server_ports = manager.list([ 60000 ])

    pool = multiprocessing.Pool(16, initializer=set_server)

    i = 0
    print(str(i) + ' out of ' + str(len(remaining_bugs)))
    for _ in pool.imap_unordered(analyze_bug, remaining_bugs, chunksize=21):
        i += 1
        print(str(i) + ' out of ' + str(len(remaining_bugs)))
        if i % 210 == 0:
            with open(os.path.join(DIR, 'analyzed_bugs.json'), 'w') as f:
                json.dump(analyzed_bugs_shared._getvalue(), f)

    with open(os.path.join(DIR, 'analyzed_bugs.json'), 'w') as f:
        json.dump(analyzed_bugs_shared._getvalue(), f)

    pool.close()
    pool.join()


    rows_per_channel = {
      'release': [],
      'beta': [],
      'aurora': [],
    }
    row_per_channel_keys = set()
    for bug_id, info in analyzed_bugs.iteritems():
        info['bug_id'] = bug_id

        # Merge info from commits.
        for commit, commit_info in info['patches'].items():
            for key in ['developer_familiarity_overall', 'code_churn_overall', 'code_churn_last_3_releases', 'reviewer_familiarity_overall', 'changes_size', 'reviewer_familiarity_last_3_releases', 'changes_del', 'test_changes_size', 'modules_num', 'changes_add', 'developer_familiarity_last_3_releases', 'languages']:
                if key in info:
                    info[key] += commit_info[key]
                else:
                    info[key] = commit_info[key]
        del info['patches']

        # Add info regarding users.
        info['bug_creator'] = info['users']['creator']['name']
        info['bug_assignee'] = info['users']['assignee']['name']
        info['patch_authors'] = '^'.join(info['users']['authors'])
        info['patch_reviewers'] = '^'.join(info['users']['reviewers'])
        del info['users']

        # Expand arrays.
        for key in info.keys():
            if isinstance(info[key], list):
                info[key] = '^'.join(list(set(info[key])))

        # Add uplift-related info.
        info_before = info.copy()
        del info_before['channels']
        for channel in ['release', 'beta', 'aurora']:
            if (channel + '_uplift_info') in info_before:
                del info_before[channel + '_uplift_info']

        for channel in ['release', 'beta', 'aurora']:
            if (channel + '_uplift_info') not in info:
                continue

            if 'uplift_date' in info[channel + '_uplift_info']:
                uplift_date = datetime.strptime(info[channel + '_uplift_info']['uplift_date'], '%Y-%m-%d')
                if uplift_date < datetime(2014, 9, 1) or uplift_date >= datetime(2016, 9, 1):
                    continue
            elif 'uplift_reject_date' in info[channel + '_uplift_info']:
                uplift_reject_date = datetime.strptime(info[channel + '_uplift_info']['uplift_reject_date'], '%Y-%m-%d')
                if uplift_reject_date < datetime(2014, 9, 1) or uplift_reject_date > datetime(2016, 9, 1):
                    continue

            row_per_channel = info_before.copy()

            info[channel + '_landing_delta'] = info[channel + '_uplift_info']['landing_delta']
            info[channel + '_response_delta'] = info[channel + '_uplift_info']['response_delta']
            info[channel + '_release_delta'] = info[channel + '_uplift_info']['release_delta']
            info[channel + '_uplift_comment_length'] = len(info[channel + '_uplift_info']['uplift_comment']['text']) if info[channel + '_uplift_info']['uplift_comment'] is not None else 0
            info[channel + '_uplift_requestor'] = info[channel + '_uplift_info']['uplift_comment']['author'] if info[channel + '_uplift_info']['uplift_comment'] is not None else ''
            info[channel + '_uplift_accepted'] = info[channel + '_uplift_info']['uplift_accepted']
            if 'uplift_date' in info[channel + '_uplift_info']:
                info[channel + '_uplift_date'] = info[channel + '_uplift_info']['uplift_date']
            if 'uplift_reject_date' in info[channel + '_uplift_info']:
                info[channel + '_uplift_reject_date'] = info[channel + '_uplift_info']['uplift_reject_date']
            del info[channel + '_uplift_info']

            row_per_channel['landing_delta'] = info[channel + '_landing_delta']
            row_per_channel['response_delta'] = info[channel + '_response_delta']
            row_per_channel['release_delta'] = info[channel + '_release_delta']
            row_per_channel['uplift_comment_length'] = info[channel + '_uplift_comment_length']
            row_per_channel['uplift_requestor'] = info[channel + '_uplift_requestor']
            row_per_channel['uplift_accepted'] = info[channel + '_uplift_accepted']
            if (channel + '_uplift_date') in info:
                row_per_channel['uplift_date'] = info[channel + '_uplift_date']
            if (channel + '_uplift_reject_date') in info:
                row_per_channel['uplift_reject_date'] = info[channel + '_uplift_reject_date']
            rows_per_channel[channel].append(row_per_channel)

            # Add keys to the set of keys.
            row_per_channel_keys |= set(row_per_channel.keys())


    row_per_channel_keys.remove('bug_id')
    row_per_channel_keys = ['bug_id'] + sorted(list(row_per_channel_keys))

    for channel in ['release', 'beta', 'aurora']:
        with open('independent_metrics/basic_' + channel + '.csv', 'w') as output_file:
            csv_writer = csv.DictWriter(output_file, row_per_channel_keys)
            csv_writer.writeheader()
            csv_writer.writerows(rows_per_channel[channel])
