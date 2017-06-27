import pandas as pd
from scipy import stats
from numpy import nanmedian
import rpy2.robjects as robjects
from rpy2.robjects.packages import importr

def bonferroniCorrection(p_value, num_tests):
    if p_value * num_tests < 1:
        return p_value * num_tests
    return 1

def effectSize(series1, series2, rcliff):
    list1 = robjects.FloatVector(list(series1))
    list2 = robjects.FloatVector(list(series2))
    effect_size = rcliff(list1, list2).rx('magnitude')[0].levels[0]
    return effect_size

def loadMetrics():
    with open('independent_metrics/metric_list.txt') as f:
        return [line.rstrip('\n') for line in f]

def loadData(channel):
    df_basic = pd.read_csv('independent_metrics/basic_{}.csv'.format(channel))
    df_review = pd.read_csv('independent_metrics/review_metrics.csv')
    df_senti = pd.read_csv('independent_metrics/senti_metrics.csv')
    df_code = pd.read_csv('independent_metrics/src_code_metrics.csv')
    df = pd.merge(df_basic, df_review, on='bug_id')
    df = pd.merge(df, df_senti, on='bug_id')
    df = pd.merge(df, df_code, on='bug_id')

    # Convert deltas from seconds to days.
    df.landing_delta = df.landing_delta / 86400
    df.response_delta = df.response_delta / 86400
    df.release_delta = df.release_delta / 86400

    # Ignore uplifts in the 'Pocket' component.
    df = df[df.component != 'Pocket']

    return df

def to_nice_num(num):
    if abs(num) < 0.01:
        return "{:.2e}".format(num)

    nice_num = "{0:.2f}".format(num)

    if nice_num.endswith('0'):
        nice_num = nice_num[:-1]

    return nice_num

def print_results(channel, df_res, columns, metric_list):
    if channel != 'aurora':
        print('\\hline')
    print('\\emph{' + channel.capitalize() + '}')

    metric_names = {
        'changes_size': 'Code churn',
        'test_changes_size': 'Test churn',
        'code_churn_overall': 'Prior changes',
        'LOC': 'LOC',
        'avg_cyclomatic': 'Average cyclomatic',
        'cnt_func': 'Number of functions',
        'maxnesting': 'Maximum nesting',
        'ratio_comment': 'Comment ratio',
        'modules_num': 'Module number',
        'page_rank': 'PageRank',
        'betweenness': 'Betweenness',
        'closeness': 'Closeness',
        'developer_familiarity_overall': 'Developer exp.',
        'reviewer_familiarity_overall': 'Reviewer exp.',
        'comments': '\\# of comments',
        'comment_words': 'Comment words',
        'review_duration': 'Review duration',
        'min_neg': 'Developer sentiment',
        'owner_neg': 'Owner sentiment',
        'landing_delta': 'Landing delta',
        'response_delta': 'Response delta',
        'release_delta': 'Release delta',
    }

    for metric in metric_list:
        metric_name = metric_names[metric]

        obj = df_res[df_res.metric == metric].iloc[0]

        # Ignore non significant results.
        if obj['effect_size'] == '--':
            continue

        p_value = to_nice_num(obj['p-value'])
        if obj['p-value'] < 0.05:
            p_value = '\\textbf{' + p_value + '}'

        print('& ' + metric_name + ' & ' + to_nice_num(obj[columns[0]]) + ' & ' + to_nice_num(obj[columns[1]]) + ' & ' + p_value + ' & ' + obj['effect_size'] + ' \\\\')

def statisticalAnalyses(df_sub1, df_sub2, metric_list):
    # import R packages
    effsize = importr('effsize')
    rcliff = robjects.r['cliff.delta']
    # list to save the results
    result_list = list()
    # Wilcoxon rank sum test & effect size
    num_tests = len(metric_list)
    for metric in metric_list:
        statistic,p_value = stats.mannwhitneyu(df_sub1[metric], df_sub2[metric])
        corrected_p = bonferroniCorrection(p_value, num_tests)
        effect_size = '--'
        if corrected_p < 0.05:
            effect_size = effectSize(df_sub1[metric], df_sub2[metric], rcliff)            
        sub1_median = nanmedian(df_sub1[metric])
        sub2_median = nanmedian(df_sub2[metric])
        result_list.append([metric, sub1_median, sub2_median, corrected_p, effect_size])
    return result_list

if __name__ == '__main__':
    for channel in ['aurora', 'beta', 'release']:
        # initialize variables
        metric_list = loadMetrics()
        # load data
        df = loadData(channel)
        # split data into different categories
        df_accept = df.loc[df.uplift_accepted == True]
        df_reject = df.loc[df.uplift_accepted == False]
        # statistical analyses
        result_list = statisticalAnalyses(df_accept, df_reject, metric_list)
        # output results
        df_res = pd.DataFrame(result_list, columns=['metric', 'accepted', 'rejected', 'p-value', 'effect_size'])
        print_results(channel, df_res, ['accepted', 'rejected'], metric_list)
