import sys, csv, os, re, subprocess
from collections import OrderedDict

# Execute a shell command
def shellCommand(command_str):
    cmd = subprocess.Popen(command_str, shell=True, stdout=subprocess.PIPE)
    cmd_out, cmd_err = cmd.communicate()
    return cmd_out

def mapRelease2Commit():
    rel2commit = list()
    with open('data/release2commit.csv') as f:
        reader = csv.reader(f)
        for row in reader:
            release = row[0]
            commit = row[1]
            rel2commit.append([release, commit])
    return rel2commit

if __name__ == '__main__':
    rel2commit = mapRelease2Commit()
    current_dir = os.getcwd()
    i = 0
    for a_pair in rel2commit[40:]:
        rel = a_pair[0]
        commit = a_pair[1]
        print 'Analysing release #%s ...' %rel
        rel_num = re.sub(r'\.', '_', rel)
        os.chdir('release')
        shellCommand('hg update -r %s' %commit)
        os.chdir(current_dir)
        in_path = 'release'
        out_path = 'udb/%s.udb' %rel_num
        shellCommand('und -db %s create -languages C++ add %s analyze' %(out_path, in_path))
        # clean memory
        shellCommand('sudo sysctl -w vm.drop_caches=3')
        i += 1
