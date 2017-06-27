import random
import json
import argparse
import os

import get_bugs

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Mine commit metrics')
    parser.add_argument('type', action='store', choices=['generate', 'validate', 'diff'])
    parser.add_argument('-n', '--num', action='store', choices=['1', '2'])
    args = parser.parse_args()

    if args.type == 'generate':
        bugs = get_bugs.__download_bugs('all_bugs', get_bugs.__get_all_bugs_query())

        # 380 is the size of the sample needed to get a 95% confidence level with 5% interval for 35815.
        bugs_sample = random.sample(bugs, 380)

        actual_bugs = get_bugs.__filter_bugs(bugs_sample)

        print(str(len(actual_bugs)) + ' identified as actual bugs out of a sample of ' + str(len(bugs_sample)) + ' bugs (the total is ' + str(len(bugs)) + ')')

        to_save = [{ 'id': bug['id'], 'is_bug': bug in actual_bugs, 'correct': None } for bug in bugs_sample]

        with open('all_bugs/bugs_to_validate_1.json', 'w') as f:
            json.dump(to_save, f)
        with open('all_bugs/bugs_to_validate_2.json', 'w') as f:
            json.dump(to_save, f)
    elif args.type == 'validate':
        if args.num is None:
            parser.print_help()
            raise Exception('Missing \'num\' argument.')

        with open('all_bugs/bugs_to_validate_' + args.num + '.json', 'r') as f:
            bugs = json.load(f)

        for bug in [b for b in bugs if b['correct'] is None]:
            os.system('firefox https://bugzilla.mozilla.org/show_bug.cgi?id=' + str(bug['id']))

            progress = str(len([e for e in bugs if e['correct']])) + ' / ' + str(len([e for e in bugs if e['correct'] is not None]))

            v = raw_input(progress + ' - Is bug ' + str(bug['id']) + ' a bug (b) or a feature (f)? (e) to exit: ')

            if v in ['e', 'exit']:
                break

            bug['correct'] = (bug['is_bug'] and v in ['b', 'bug']) or (not bug['is_bug'] and v in ['f', 'feature'])

        with open('all_bugs/bugs_to_validate_' + args.num + '.json', 'w') as f:
            json.dump(bugs, f)
    elif args.type == 'diff':
        with open('all_bugs/bugs_to_validate_1.json', 'r') as f:
            bugs_1 = json.load(f)
        with open('all_bugs/bugs_to_validate_2.json', 'r') as f:
            bugs_2 = json.load(f)
        with open('all_bugs/bugs_to_validate_decision.json', 'r') as f:
            bugs_decision = json.load(f)

        diff = 0

        for i in range(0, len(bugs_1)):
            if bugs_1[i]['correct'] != bugs_2[i]['correct']:
                print(str(bugs_1[i]['id']) + ', 1 ' + str(bugs_1[i]['correct']) + ', 2 ' + str(bugs_2[i]['correct']))
                diff += 1

        true_positives_1 = len([bug for bug in bugs_1 if bug['is_bug'] and bug['correct']])
        true_negatives_1 = len([bug for bug in bugs_1 if not bug['is_bug'] and bug['correct']])
        false_positives_1 = len([bug for bug in bugs_1 if bug['is_bug'] and not bug['correct']])
        false_negatives_1 = len([bug for bug in bugs_1 if not bug['is_bug'] and not bug['correct']])
        true_positives_2 = len([bug for bug in bugs_2 if bug['is_bug'] and bug['correct']])
        true_negatives_2 = len([bug for bug in bugs_2 if not bug['is_bug'] and bug['correct']])
        false_positives_2 = len([bug for bug in bugs_2 if bug['is_bug'] and not bug['correct']])
        false_negatives_2 = len([bug for bug in bugs_2 if not bug['is_bug'] and not bug['correct']])

        print('Diff on ' + str(diff) + ' bugs.')
        print('Accuracy1: {:.3%}'.format(float(true_positives_1 + true_negatives_1) / len(bugs_1)))
        print('Precision1: {:.3%}'.format(float(true_positives_1) / (true_positives_1 + false_positives_1)))
        print('Recall1: {:.3%}'.format(float(true_positives_1) / (true_positives_1 + false_negatives_1)))
        print('Specificity1: {:.3%}'.format(float(true_negatives_1) / (true_negatives_1 + false_positives_1)))
        print('')
        print('Accuracy2: {:.3%}'.format(float(true_positives_2 + true_negatives_2) / len(bugs_2)))
        print('Precision2: {:.3%}'.format(float(true_positives_2) / (true_positives_2 + false_positives_2)))
        print('Recall2: {:.3%}'.format(float(true_positives_2) / (true_positives_2 + false_negatives_2)))
        print('Specificity2: {:.3%}'.format(float(true_negatives_2) / (true_negatives_2 + false_positives_2)))
        print('')

        true_positives_decision = len([bug for bug in bugs_decision if bug['is_bug'] and bug['correct']])
        true_negatives_decision = len([bug for bug in bugs_decision if not bug['is_bug'] and bug['correct']])
        false_positives_decision = len([bug for bug in bugs_decision if bug['is_bug'] and not bug['correct']])
        false_negatives_decision = len([bug for bug in bugs_decision if not bug['is_bug'] and not bug['correct']])

        print('Accuracy: {:.3%}'.format(float(true_positives_decision + true_negatives_decision) / len(bugs_decision)))
        print('Precision: {:.3%}'.format(float(true_positives_decision) / (true_positives_decision + false_positives_decision)))
        print('Recall: {:.3%}'.format(float(true_positives_decision) / (true_positives_decision + false_negatives_decision)))
        print('Specificity: {:.3%}'.format(float(true_negatives_decision) / (true_negatives_decision + false_positives_decision)))
