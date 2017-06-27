from libmozdata import bugzilla
from libmozdata.utils import get_date_ymd

# Assume query ends with 'limit=500&order=bug_id&fXXX=bug_id&oXXX=greaterthan&vXXX='.
def get_ids(query):
    ids = []

    while True:
        new_ids = []

        def bughandler(bug):
            ids.append(bug['id'])
            new_ids.append(bug['id'])

        bugzilla.Bugzilla(query + str(max(ids) if len(ids) > 0 else 0) + '&include_fields=id', bughandler=bughandler).get_data().wait()

        if len(new_ids) < 500:
            break

    return ids


# Given a list of bugs and a query, returns the IDs of the bugs that
# the query returns and that are not in the list.
def get_missing_bugs(bugs, query):
    return set(get_ids(query)).difference(set([bug['id'] for bug in bugs]))


UPLIFT_FLAG_NAMES = ['approval-mozilla-release', 'approval-mozilla-beta', 'approval-mozilla-aurora']


def get_uplifts(bugs):
    return [bug for bug in bugs if any(flag['name'] in UPLIFT_FLAG_NAMES and flag['status'] == '+' for attachment in bug['attachments'] for flag in attachment['flags'])]


def uplift_channels(bug):
    channels = set()

    for attachment in bug['attachments']:
        for flag in attachment['flags']:
            if flag['name'] not in UPLIFT_FLAG_NAMES:
                continue

            channels.add(flag['name'][17:])

    return list(channels)


def uplift_approved_channels(bug):
    channels = set()

    for attachment in bug['attachments']:
        for flag in attachment['flags']:
            if flag['name'] not in UPLIFT_FLAG_NAMES or flag['status'] != '+':
                continue

            channels.add(flag['name'][17:])

    return list(channels)


def get_uplift_date(bug, channel):
    for attachment in bug['attachments']:
        for flag in attachment['flags']:
            if flag['name'] != 'approval-mozilla-' + channel or flag['status'] != '+':
                continue

            return get_date_ymd(flag['creation_date'])


def get_uplift_reject_date(bug, channel):
    for attachment in bug['attachments']:
        for flag in attachment['flags']:
            if flag['name'] != 'approval-mozilla-' + channel or flag['status'] != '-':
                continue

            return get_date_ymd(flag['creation_date'])


def get_bug_types(bug):
    types = []

    crash_keywords = ['crash', 'jsbugmon', 'topcrash', 'assertion', 'stack-wanted',
                      'crashreportid']
    crash_title_keywords = ['npe', 'crash', 'addresssanitizer', 'heap overflow', 'race condition', ]
    if bug['cf_crash_signature'] != '' or any(keyword in bug['keywords'] for keyword in crash_keywords) or any(keyword in bug['summary'].lower() for keyword in crash_title_keywords):
        types.append('crash')

    sec_keywords = ['sec-', 'csectype-',]
    sec_title_keywords = ['uaf', 'use-after-free', ]
    if any(sub_keyword in keyword for sub_keyword in sec_keywords for keyword in bug['keywords']):
        types.append('security')

    feature_keywords = ['feature', 'polish']
    feature_title_keywords = ['[ux]', 'implement', 'support']
    if any(keyword in bug['keywords'] for keyword in feature_keywords) or any(keyword in bug['summary'].lower() for keyword in feature_title_keywords) or '[ux]' in bug['whiteboard'].lower():
        types.append('feature')

    performance_keywords = ['hang', 'talos-regression', 'perf']
    performance_title_keywords = ['slow', 'performance']
    if any(keyword in bug['keywords'] for keyword in performance_keywords) or any(keyword in bug['summary'].lower() for keyword in performance_title_keywords) or 'memshrink' in bug['whiteboard'].lower():
        types.append('performance')

    return types
