import csv

import pandas as pd
import regex as re
from git import Repo


def export_commit_history(repo_path, csv_path):
    repo = Repo(path=repo_path)
    commits = list(repo.iter_commits())[::-1]

    # get all keys in csv

    df=pd.read_csv(csv_path)
    keys = set(df['key'])

    for commit in commits:
        if str(commit.message).startswith('Set key '):
            key = re.search(r'\"(.+?)\"', commit.message).group(1)
            if key in keys:
                # print(commit.committed_datetime, key)

                df.loc[df['key'] == key, 'date'] = commit.committed_datetime.strftime('%Y-%m-%d %H:%M:%S')

    df.to_csv(csv_path, index=False)




def add_hide_column(csv_path):
    df = pd.read_csv(csv_path)
    df['hide'] = False
    df.to_csv(csv_path, index=False)


if __name__ == "__main__":
    # `cp ~/.gitlinks/index.csv .`
    export_commit_history('~/.gitlinks/.git', 'index.csv')
    # add_hide_column('index.csv')


