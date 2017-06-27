from __future__ import division
import json, re, string, pprint
from datetime import datetime
from numpy import mean
import get_bugs
import pandas as pd

def relatedComments(bug_item, attach_id):
    total_times, total_words = 0, 0
    commenter_set = set()
    for comment_item in bug_item['comments']:
        commenter_set.add(comment_item['author'])
        raw_comment = comment_item['text']
        matched = re.findall(r'Review of attachment ([0-9]+)', raw_comment)
        if len(matched):
            if attach_id == int(matched[0]):
                comment_times, comment_words = 0, 0
                for line in raw_comment.split('\n')[2:]:
                    if not (line.startswith('>') or line.startswith('Review of attachment') or line.startswith('(In reply to')):
                        if re.search(r'[a-zA-Z]', line):
                            comment_words += len(re.findall(r'\S+', line.encode('utf-8').translate(None, string.punctuation)))
                            comment_times += 1
                total_times += comment_times
                total_words += comment_words
    return total_times, total_words, commenter_set

# Compute date interval between two date strings
def dateDiff(d1_str, d2_str):
    d1 = datetime.strptime(d1_str, '%Y%m%d%H%M%S')
    d2 = datetime.strptime(d2_str, '%Y%m%d%H%M%S')
    return (d2 - d1).total_seconds()/3600

if __name__ == '__main__':
    DEBUG = False    
    # load bugs
    if DEBUG:
        bug_list = ()
        with open('all_bugs/all_bugs0.json') as f:
            bug_list = json.load(f)[:50]
    else:
        print 'Loading bug reports ...'
        all_bugs = get_bugs.get_all()
        if DEBUG:
            bug_list = all_bugs[:5]
        else:
            bug_list = all_bugs
    # extracting review metrics
    print 'Extracting metrics ...'
    output_list = list()
    metric_names = ['bug_id', 'review_iterations', 'comment_times', 'comment_words', 'reviewer_cnt', 'reviewer_comment_rate', 
                    'non_author_voters', 'neg_review_rate', 'response_delay', 'review_duration', 
                    'feedback_count', 'neg_feedbacks', 'feedback_delay', 'review_status']
    for bug_item in bug_list:
        bug_id = bug_item['id']
        print bug_id
        total_patches, approved_patches, obsolete_cnt = 0, 0, 0
        iteration_list, ct_list, cw_list, reviewer_cnt_list, reviewer_comm_list = list(), list(), list(), list(), list()
        n_author_list, neg_review_list, review_delay_list, review_dur_list = list(), list(), list(), list()
        fb_cnt_list, fb_neg_list, fb_delay_list = list(), list(), list()
        for attach_item in bug_item['attachments']:
            if attach_item['is_patch']:
                if attach_item['content_type'] == 'text/plain':
                    attach_id = attach_item['id']
                    attach_flags = attach_item['flags']
                    attach_author = attach_item['creator']
                    attach_date = re.sub(r'[^0-9]', '', attach_item['creation_time'])
                    is_obsolete = attach_item['is_obsolete']
                    # analyze patches (including the obsolete ones)
                    if len(attach_flags):
                        print 'attach:', attach_id
                        # count total reviewed or review requested patches
                        total_patches += 1
                        # count obsolete patches in a bug
                        if is_obsolete == 1:
                            obsolete_cnt += 1
                        review_iterations = 0
                        feedback_cnt, neg_feedbacks = 0, 0
                        reviewer_set = set()
                        first_review_date, last_review_date, first_feedback_date = None, None, None
                        pos_votes, neg_votes = 0, 0
                        for a_flag in attach_flags:
                            if 'review' in a_flag['name']:
                                if first_review_date == None:
                                    first_review_date = re.sub(r'[^0-9]', '', a_flag['modification_date'])
                                last_review_date = re.sub(r'[^0-9]', '', a_flag['modification_date'])
                                reviewer_set.add(a_flag['setter'])
                                if a_flag['status'] == '+':
                                    pos_votes += 1
                                elif a_flag['status'] == '-':
                                    neg_votes += 1
                                review_iterations += 1
                            elif 'feedback' in a_flag['name']:
                                if first_feedback_date == None:
                                    first_feedback_date = re.sub(r'[^0-9]', '', a_flag['modification_date'])
                                if a_flag['status'] == '-':
                                    neg_feedbacks += 1
                                feedback_cnt += 1
                        iteration_list.append(review_iterations)
                        fb_cnt_list.append(feedback_cnt)
                        reviewer_cnt_list.append(len(reviewer_set))
                        # proportion of negative reviews
                        if pos_votes + neg_votes:
                            neg_review_rate =  neg_votes/(pos_votes+neg_votes)
                        else:
                            neg_review_rate = -1
                        neg_review_list.append(neg_review_rate)
                        # number of negative feedbacks
                        fb_neg_list.append(neg_feedbacks)
                        # non author voters
                        non_author_voters = len(reviewer_set - set([attach_author]))
                        n_author_list.append(non_author_voters)
                        # review delay and review duration
                        if first_review_date:
                            response_delay = dateDiff(attach_date, first_review_date)
                            review_duration = dateDiff(attach_date, last_review_date)
                        else:
                            response_delay = -1
                            review_duration = -1
                        review_delay_list.append(response_delay)
                        review_dur_list.append(review_duration)
                        # feedback delay
                        if first_feedback_date:
                            feedback_delay = dateDiff(attach_date, first_feedback_date)
                        else:
                            feedback_delay = -1
                        fb_delay_list.append(feedback_delay)
                        # comment metrics
                        total_comment_times, total_comment_words, commenter_set = relatedComments(bug_item, attach_id)
                        if len(reviewer_set):
                            reviewer_comment_rate = len(reviewer_set-commenter_set) / len(reviewer_set)
                        else:
                            reviewer_comment_rate = 0
                        reviewer_comm_list.append(reviewer_comment_rate)
                        ct_list.append(total_comment_times)
                        cw_list.append(total_comment_words)
                        # whether the patched has been approved
                        if attach_flags[-1]['status'] == '+':
                            approved_patches += 1
        if total_patches:
            obsolete_patch_rate = obsolete_cnt/total_patches
            if approved_patches/total_patches == 1:
                review_status = '+'
            else:
                review_status = '?'
            output_list.append([bug_id, mean(iteration_list), mean(ct_list), mean(cw_list), mean(reviewer_cnt_list), mean(reviewer_comm_list), 
                                mean(n_author_list), mean(neg_review_list), mean(review_delay_list), mean(review_dur_list),
                                mean(fb_cnt_list), mean(fb_neg_list), mean(fb_delay_list), review_status])
            
        else:
            obsolete_patch_rate = 0
    # output results
    df = pd.DataFrame(output_list, columns=metric_names).round(decimals=2).fillna(-1)    
    df.to_csv('independent_metrics/review_metrics.csv', index=False)
    if DEBUG:
        print df
        
