# Is It Safe to Uplift This Patch? - An Empirical Study on Mozilla Firefox

### Requirements
- Python 2.7 or newer
- Python 3.4 or newer
- R 3.2 or newer

### Research questions
- RQ1: What are the characteristics of patches that are uplifted?
- RQ2: What are the characteristics of uplifted patches that introduced faults in the system?

### Data mining scripts
- **bug_inducing.py**: identifies fault-inducing patches based on the SZZ algorithm.
- **complexity_sna** folder: compute source code metrics againt the Understand and igraph tools. The results will then be extracted and pretty outputted by **src_code_metrics.py**.
- **analyze_bugs.py**: extract some metrics about review and uplift process, developer/reviewer familiarity, etc..
- **senti_metrics.py**: extract sentiment metrics from the comments in the issue reports.
- **review_metrics.py**: extract code review-related metrics from comments and patch flags in the issue reports.

### Data Analysis scripts
- **comparison_acceptation.py**: performs Wilcoxon rank sum test and Cliff's data effect size analysis to compare the characteristics between accepted pathces and rejected patches for uplift.
- **comparison_failure.py**:  performs Wilcoxon rank sum test and Cliff's data effect size analysis to compare the characteristics between fault-inducing patches and clean patches that are uplifted.

### Data folder
- **independent_metrics** folder contains all metrics calculated for statistical analyses along various dimentions.
 
### How to user the analytic scripts
1. Consecutively execute the data mining scripts to extract data for statistical analyses.
2. Execute the data analysis scripts to compare characteristics between accepted vs. rejected patches (RQ1), and between fault-inducing vs. clean patches (RQ2).

### Data source
- Bugzilla: https://www.bugzilla.org
- Mozilla source code: https://developer.mozilla.org/en-US/docs/Mozilla/Developer_guide/Source_Code/Downloading_Source_Archives

### Tool
- Understand: https://scitools.com/
- igraph: http://igraph.org
