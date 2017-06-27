import sys
import os
import copy
import json
import gzip
import math
import re
from pprint import pprint
from libmozdata import bugzilla


# Assumes query doesn't use the f1 field.
def __download_bugs(name, query):
    bugs = []

    i = 0
    while True:
        try:
            with open(name + '/' + name + str(i) + '.json', 'r') as f:
                bugs += json.load(f)
            i += 1
        except IOError:
            break

    print('Loaded ' + str(len(bugs)) + ' bugs.')

    search_query = query + '&limit=500&order=bug_id&f1=bug_id&o1=greaterthan&v1='

    last_id = max([bug['id'] for bug in bugs]) if len(bugs) > 0 else 0

    ATTACHMENT_INCLUDE_FIELDS = [
        'id', 'creation_time', 'is_obsolete', 'flags', 'is_patch', 'creator', 'content_type',
    ]

    COMMENT_INCLUDE_FIELDS = [
        'id', 'text', 'author', 'time',
    ]

    found = []
    finished = False
    while not finished:
        bugs_dict = dict()

        def bughandler(bug):
            bugid = str(bug['id'])

            if bugid not in bugs_dict:
                bugs_dict[bugid] = dict()

            for k, v in bug.items():
                bugs_dict[bugid][k] = v

        def commenthandler(bug, bugid):
            bugid = str(bugid)

            if bugid not in bugs_dict:
                bugs_dict[bugid] = dict()

            bugs_dict[bugid]['comments'] = bug['comments']

        def attachmenthandler(bug, bugid):
            bugid = str(bugid)

            if bugid not in bugs_dict:
                bugs_dict[bugid] = dict()

            bugs_dict[bugid]['attachments'] = bug

        def historyhandler(bug):
            bugid = str(bug['id'])

            if bugid not in bugs_dict:
                bugs_dict[bugid] = dict()

            bugs_dict[bugid]['history'] = bug['history']

        bugzilla.Bugzilla(search_query + str(last_id), bughandler=bughandler, commenthandler=commenthandler, comment_include_fields=COMMENT_INCLUDE_FIELDS, attachmenthandler=attachmenthandler, attachment_include_fields=ATTACHMENT_INCLUDE_FIELDS, historyhandler=historyhandler).get_data().wait()

        found = list(bugs_dict.values())

        last_id = max([last_id] + [bug['id'] for bug in found])

        bugs += found

        print('Total number of bugs: ' + str(len(bugs)))

        if len(found) != 0 and (len(bugs) % 5000 == 0 or len(found) < 500):
            for i in range(0, int(math.ceil(float(len(bugs)) / 1000))):
                with open(name + '/' + name + str(i) + '.json', 'w') as f:
                    json.dump(bugs[i*1000:(i+1)*1000], f)

        if len(found) < 500:
            finished = True

    return bugs


def __filter_bugs(bugs):
    # Example bug data: https://bugzilla.mozilla.org/rest/bug/679352
    # Example bug comments data: https://bugzilla.mozilla.org/rest/bug/679352/comment
    # Example bug history data: https://bugzilla.mozilla.org/rest/bug/679352/history

    # If the bug contains these keywords, it's very likely a feature.
    def feature_check_keywords(bug):
        keywords = [
            'feature'
        ]
        return any(keyword in bug['keywords'] for keyword in keywords)

    # If the Severity (Importance) field's value is "enhancement", it's likely not a bug
    def check_severity_enhance(bug):
        if bug['severity'] == 'enhancement':
            return True
        return False

    feature_rules = [
        feature_check_keywords,
        check_severity_enhance,
    ]

    # If the bug has a crash signature, it is definitely a bug.
    def has_crash_signature(bug):
        return bug['cf_crash_signature'] != ''

    # If the bug has steps to reproduce, it is very likely a bug.
    def has_str(bug):
        return 'cf_has_str' in bug and bug['cf_has_str'] == 'yes'

    # If the bug has a regression range, it is definitely a bug.
    def has_regression_range(bug):
        return 'cf_has_regression_range' in bug and bug['cf_has_regression_range'] == 'yes'

    # If the bug has a URL, it's very likely a bug that the reporter experienced
    # on the given URL.
    def has_url(bug):
        return bug['url'] != ''

    # If the bug contains these keywords, it's definitely a bug.
    def bug_check_keywords(bug):
        keywords = [
            'crash', 'regression', 'regressionwindow-wanted', 'jsbugmon',
            'hang', 'topcrash', 'assertion', 'coverity', 'infra-failure',
            'intermittent-failure', 'reproducible', 'stack-wanted',
            'steps-wanted', 'testcase-wanted', 'testcase', 'crashreportid',
        ]
        return any(keyword in bug['keywords'] for keyword in keywords)

    # If the bug title contains these substrings, it's definitely a bug.
    def bug_check_title(bug):
        keywords = [
            'failur', 'fail', 'npe', 'except', 'broken', 
            'crash', 'bug', 'differential testing', 'error',
            'addresssanitizer', 'hang ', ' hang', 'jsbugmon', 'leak', 'permaorange',
            'random orange', 'intermittent', 'regression', 'test fix',
            'heap overflow',
        ]
        return any(keyword in bug['summary'].lower() for keyword in keywords)

    # If the first comment in the bug contains these substrings, it's likely a bug.
    def check_first_comment(bug):
        keywords = [
            'steps to reproduce', 'crash', 'assertion', 'failure', 'leak', 'stack trace', 'regression',
            'test fix', ' hang', 'hang ', 'heap overflow', 'str:',
        ]
        return any(keyword in bug['comments'][0]['text'].lower() for keyword in keywords)

    # If any of the comments in the bug contains these substirngs, it's likely a bug.
    def check_comments(bug):
        keywords = [
            'mozregression', 'safemode', 'safe mode',
            # mozregression messages.
            'Looks like the following bug has the changes which introduced the regression', 'First bad revision',
        ]
        return any(keyword in comment['text'].lower() for comment in bug['comments'] for keyword in keywords)

    # If the Severity (Importance) field's value is "major", it's likely a bug
    def check_severity_major(bug):
        if bug['severity'] == 'major':
            return True
        return False

    def is_coverity_issue(bug):
        return re.search('[CID ?[0-9]+]', bug['summary']) or re.search('[CID ?[0-9]+]', bug['whiteboard'])

    bug_rules = [
        has_crash_signature,
        has_str,
        has_regression_range,
        has_url,
        bug_check_keywords,
        bug_check_title,
        check_first_comment,
        check_comments,
        check_severity_major,
        is_coverity_issue,
    ]

    return [bug for bug in bugs if any(rule(bug) for rule in bug_rules) and not any(rule(bug) for rule in feature_rules)]


# All RESOLVED/VERIFIED FIXED bugs in the Firefox and Core products filed and resolved between 2014-07-22 (release date of 31.0) and 2016-08-24 (release date of 48.0.2).
def __get_all_bugs_query():
    return 'product=Core&product=Firefox&' +\
    'bug_status=RESOLVED&bug_status=VERIFIED&resolution=FIXED&' +\
    'f2=creation_ts&o2=greaterthan&v2=2014-07-22&f3=creation_ts&o3=lessthan&v3=2016-08-24&' +\
    'f4=cf_last_resolved&o4=lessthan&v4=2016-08-24'


def get_all():
    return __download_bugs('all_bugs', __get_all_bugs_query())


def get_all_bugs():
    return __filter_bugs(__download_bugs('all_bugs', __get_all_bugs_query()))


if __name__ == '__main__':
    print('Total number of actual bugs: ' + str(len(get_all_bugs())))
