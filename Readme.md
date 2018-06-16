# Is It Safe to Uplift This Patch? - An Empirical Study on Mozilla Firefox

### Requirements
- Python 2.7 or newer
- Python 3.4 or newer
- R 3.2 or newer

### Research questions
- RQ1: What are the characteristics of patches that are uplifted?
- RQ2: How effective are uplift operations?
- RQ3: What are the characteristics of uplifted patches that introduced faults in the system?
- RQ4: Are regressions caused by uplift more severe than the bugs that were fixed with the uplift?
- RQ5: Could some of the regressions have been prevented through more exten- sive testing on the channels?

### Data mining scripts
- **bug_inducing.py**: identifies fault-inducing patches based on the SZZ algorithm.
- **complexity_sna** folder: compute source code metrics againt the Understand and igraph tools. The results will then be extracted and pretty outputted by **src_code_metrics.py**.
- **analyze_bugs.py**: extract some metrics about review and uplift process, developer/reviewer familiarity, etc..
- **senti_metrics.py**: extract sentiment metrics from the comments in the issue reports.
- **review_metrics.py**: extract code review-related metrics from comments and patch flags in the issue reports.

### Data Analysis scripts
- **comparison_acceptation.py**: performs Mann-Whitney U test and Cliff's data effect size analysis to compare the characteristics between accepted pathces and rejected patches for uplift.
- **comparison_failure.py**:  performs Mann-Whitney U test and Cliff's data effect size analysis to compare the characteristics between fault-inducing patches and clean patches that are uplifted.
- **sample_analyses.ipynb**: shows the statistics on the manual analysis results of RQ2, RQ4, and RQ5. 

### Data folder
- **independent_metrics** folder contains all metrics calculated for statistical analyses along various dimentions.
 
### How to user the analytic scripts
1. Generate `commit_date.csv` by executing the following command: `hg log --template '{node|short}\t{date|isodate}\n' > commit_date.csv`.
2. Consecutively execute the data mining scripts to extract data for statistical analyses.
3. Execute the data analysis scripts to compare characteristics between accepted vs. rejected patches (RQ1), and between fault-inducing vs. clean patches (RQ2).

### Data source
- Bugzilla: https://www.bugzilla.org
- Mozilla source code: https://developer.mozilla.org/en-US/docs/Mozilla/Developer_guide/Source_Code/Downloading_Source_Archives

### Tool
- Understand: https://scitools.com/
- igraph: http://igraph.org

### Other
- **presentation_ICSME.pdf** presentation slides at ICSME 2017.
