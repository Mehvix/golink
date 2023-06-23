"""GitLinks: Command line client for managing GitHub pages-powered shortlinks.
See https://github.com/lengstrom/gitlinks#setup for setup and additional usage
information.

Usage:
  gitlinks init <git_remote>
  gitlinks set <key> <url>
  gitlinks delete <key> ...
  gitlinks show
  gitlinks hide <key> ...
  gitlinks cname <CNAME>

Options:
  -h --help     Show this screen.
"""
import json
import shutil
import sys
from pathlib import Path

import git
import pandas as pd
import tabulate
from docopt import docopt
from ilock import ILock

from .utils import (ARROW, bolded, check_repo, clean, clone, commit_push,
                    generate_pages, load_csv, patch_url, plural_msg, pprint,
                    query_yes_no, reset_origin, serialize_csv, try_setup,
                    try_state)

GIT_PATH = Path('~/.gitlinks-plus/').expanduser()
INDEX_NAME = 'index.csv'
META_NAME = 'state.json'

def get_state():
    return try_state(GIT_PATH, META_NAME)

def set_state(k, v):
    state = get_state()
    state[k] = v
    json.dump(state, open(GIT_PATH / META_NAME, 'w+'))
    return state

def initialize(url, path=GIT_PATH):
    if path.exists():
        msg = f'{path} already exists; really delete?'
        if query_yes_no(msg, default='yes'):
            shutil.rmtree(path)
        else:
            pprint('Ok, exiting.')
            return

    repo = clone(url, path)
    try_setup(repo, path, INDEX_NAME, META_NAME)
    pprint(f'Initialized gitlinks via {url}!')

def set_link(key, url, df):
    url = patch_url(url)
    df = df[df.key != key]
    df = pd.concat([df, pd.DataFrame({
        'date':[pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')],
        'key':[key],
        'url':[url],
        'hide':[False],
    })], ignore_index=True, axis=0)

    return df

def delete_links(keys, df):
    keys = set(keys)
    return df[~df.key.isin(keys)]

def hide_links(keys, df):
    keys = set(keys)
    df.loc[df.key.isin(keys), 'hide'] = ~df.loc[df.key.isin(keys), 'hide']
    return df

def show(df, repo):
    df[ARROW] = [ARROW for _ in range(df.shape[0])]
    new_order = [0, 2, 1]
    df = df[df.columns[new_order]]
    df = df.sort_values('key')

    rurl = repo.remotes.origin.url
    title = bolded(f'== GitLinks (Remote: {rurl}) ==')
    print(title)
    if df.shape[0] > 0:
        tab = tabulate.tabulate(df, df.columns, colalign=('left', 'center', 'left'),
                                showindex=False)
        # width = tab.split('\n')[0].index(ARROW) - len(title)//2
        # width = min(0, width)
        # print(' ' * width + title)
        rows = '\n'.join(tab.split('\n')[2:])
        print(rows)
    else:
        pprint('Empty, no keys to display!')

    state = get_state()
    if len(state.keys()) > 0:
        pprint('State:')
        for k, v in state.items():
            pprint(f'=> {k} = {v}')

def execute(args, git_path=GIT_PATH):
    if args['init']:
        return initialize(args['<git_remote>'], path=git_path)

    try:
        repo = git.Repo(git_path)
        assert check_repo(repo, INDEX_NAME)
    except:
        msg = "No initialized repo; run `gitlinks init <url>` first!"
        raise ValueError(msg)

    csv_path = git_path / INDEX_NAME
    df = load_csv(csv_path)

    reset_origin(repo)
    clean(repo)
    pprint(f'Checking for changes from remote...')
    repo.remotes.origin.pull()

    if args['show']:
        return show(df, repo)

    if args['set']:
        key = args['<key>'][0]
        assert key[-1] != '/', f'Key "{key}" should not end with a "/"!'
        url = args['<url>']
        df = set_link(key, url, df)
        print_msg = f'Set key "{bolded(key)}" {bolded(ARROW)} "{bolded(url)}"'
        commit_msg = f'Set key "{key}" {ARROW} "{url}"'
    elif args['delete']:
        keys = args['<key>']
        poss = set(df.key)
        deletable = [k for k in keys if k in poss]
        df = delete_links(deletable, df)

        not_deletable = set(keys) - set(deletable)
        if not_deletable:
            msg = 'Key{plural} {keys_pretty} not present...'
            pprint(plural_msg(not_deletable, msg))

        msg = 'Deleted key{plural} {keys_pretty}'
        print_msg = plural_msg(deletable, msg, bold=True)
        commit_msg = plural_msg(deletable, msg, bold=False)

        if len(deletable) == 0:
            pprint('No keys to remove, exiting!')
            return
    elif args['hide']:
        keys = args['<key>']
        poss = set(df.key)
        hideable = [k for k in keys if k in poss]
        df = hide_links(hideable, df)

        not_hideable = set(keys) - set(hideable)
        if not_hideable:
            msg = 'Key{plural} {keys_pretty} not present...'
            pprint(plural_msg(not_hideable, msg))

        msg = '(un)hid key{plural} {keys_pretty}'
        print_msg = plural_msg(hideable, msg, bold=True)
        commit_msg = plural_msg(hideable, msg, bold=False)

        if len(hideable) == 0:
            pprint('No keys to (un)hide, exiting!')
            return

    if args['cname']:
        cname = args['<CNAME>']
        set_state('CNAME', cname)
        print_msg = f'Set CNAME to {cname}.'
        commit_msg = print_msg
    else:
        cname = None

    serialize_csv(df, csv_path)
    generate_pages(df, git_path, INDEX_NAME, get_state())

    try:
        pprint('Committing and pushing...')
        commit_push(repo, commit_msg[:50])
        pprint(f'{bolded("Success")}: {print_msg}.')
    except Exception as e:
        reset_origin(repo)
        pprint(f'Failed; rolling back.')
        raise e

def main():
    if len(sys.argv) == 1:
        sys.argv.append('-h')

    args = docopt(__doc__)
    with ILock('gitlinks'):
        execute(args)

if __name__ == '__main__':
    main()
