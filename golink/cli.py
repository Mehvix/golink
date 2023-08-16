"""
GoLink: Command line client for managing GitHub pages-powered shortlinks.
Forked from [GitLinks](https://github.com/lengstrom/gitlinks)
See https://github.com/mehvix/golink#setup for setup and additional usage
information.

Usage:
  golink init <git_remote>
  golink migrate
  golink set <key> <url>
  golink delete <key> ...
  golink show
  golink hide <key> ...
  golink cname <CNAME>

Options:
  -h --help     Show this screen.
"""
# TODO use argparse

import json
import re
import shutil
import sys
from pathlib import Path

import git
import pandas as pd
import tabulate
from docopt import docopt
from git.repo import Repo
from ilock import ILock
from utils import (ARROW, bolded, check_repo, clean, clone, commit_push,
                   generate_pages, load_csv, patch_url, plural_msg, pprint,
                   query_yes_no, reset_origin, serialize_csv, try_setup,
                   try_state)

GIT_PATH = Path("~/.golink/").expanduser()
INDEX_NAME = "index.csv"
META_NAME = "state.json"


def get_state():
    return try_state(GIT_PATH, META_NAME)


def set_state(k, v):
    state = get_state()
    state[k] = v
    with open(GIT_PATH / META_NAME, "w+") as fout:
        json.dump(state, fout)
    return state


def rm_dir(path, msg) -> bool:
    if query_yes_no(msg, default="yes"):
        shutil.rmtree(path)
        return True
    else:
        pprint("Ok, exiting.")
        return False


def initialize(url, path=GIT_PATH):
    if path.exists() and not rm_dir(path, msg=f"{path} already exists; re-init and delete?"):
        return

    repo = clone(url, path)
    try_setup(repo, path, INDEX_NAME, META_NAME)
    pprint(f"Initialized golink via {url}!")


def migrate(path_from="~/.gitlinks", path_to=GIT_PATH):
    """
    Migrate from GitLinks to GoLink.
    """
    path_from = Path(path_from).expanduser()
    path_to = Path(path_to).expanduser()

    if path_to.exists() and not rm_dir(path_to, msg=f"{path_to} already exists; really migrate and clean (delete) here?"):
        return

    # copy
    shutil.copytree(path_from, path_to)

    repo = Repo(path=path_to)
    git_remote_url = repo.remotes.origin.url
    commits = list(repo.iter_commits())[::-1]

    csv_path = path_to / INDEX_NAME
    df = load_csv(csv_path)

    # add date column, based on git commit information
    keys = set(df['key'])
    # for commit in tqdm(commits):
    for commit in commits:
        if str(commit.message).startswith('Set key '):
            key = re.search(r'\"(.+?)\"', commit.message).group(1)
            if key in keys:
                df.loc[df['key'] == key, 'date'] = commit.committed_datetime.strftime('%Y-%m-%d %H:%M:%S')

    # create hide column; init to False
    df['hide'] = False
    df.to_csv(csv_path, index=False)

    serialize_csv(df, csv_path)

    generate_pages(df, path_to, INDEX_NAME, get_state(), rurl=git_remote_url)

    try:
        pprint("Committing and pushing...")
        # presumably, this is a soft enforcement? I want links to not be cut off
        commit_push(repo, "Migrating from GitLinks to GoLink.")  # [:50]
        pprint(f'{bolded("Success")}: Migration succeeded.')
    except Exception as e:
        reset_origin(repo)
        pprint(f"Failed; rolling back.")
        raise e


def set_link(key, url, df):
    url = patch_url(url)
    datetime = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    df = df[df.key != key]
    df = pd.concat([df, pd.DataFrame({
        'date': [datetime],
        'key':  [key],
        'url':  [url],
        'hide': [False],
    })], ignore_index=True, axis=0)

    return df


def delete_links(keys, df):
    keys = set(keys)
    return df[~df.key.isin(keys)]


def hide_links(keys, df):
    """
    Toggle the visibility of the given keys.
    """
    keys = set(keys)
    df.loc[df.key.isin(keys), "hide"] = ~df.loc[df.key.isin(keys), "hide"]
    return df


def show(df, repo):
    # TODO fix this
    df[ARROW] = [ARROW for _ in range(df.shape[0])]
    new_order = [0, 2, 1]
    df = df[df.columns[new_order]]
    df = df.sort_values("key")

    rurl = repo.remotes.origin.url
    title = bolded(f"== golink (remote: {rurl}) ==")
    print(title)
    if df.shape[0] > 0:
        tab = tabulate.tabulate(
            df, df.columns, colalign=("left", "center", "left"), showindex=False
        )
        # width = tab.split('\n')[0].index(ARROW) - len(title)//2
        # width = min(0, width)
        # print(' ' * width + title)
        rows = "\n".join(tab.split("\n")[2:])
        print(rows)
    else:
        pprint("Empty, no keys to display!")

    state = get_state()
    if len(state.keys()) > 0:
        pprint("State:")
        for k, v in state.items():
            pprint(f"=> {k} = {v}")


def execute(args, git_path=GIT_PATH):
    if args["init"]:
        return initialize(args["<git_remote>"], path=git_path)
    if args["migrate"]:
        return migrate(path_to=git_path)

    try:
        repo = Repo(path=git_path)
        assert check_repo(repo, INDEX_NAME)
    except:
        msg = "No initialized repo; run `golink init <url>` first!"
        raise ValueError(msg)

    csv_path = git_path / INDEX_NAME
    df = load_csv(csv_path)

    reset_origin(repo)
    clean(repo)
    pprint(f"Checking for changes from remote...")
    repo.remotes.origin.pull()

    if args["show"]:
        return show(df, repo)

    if args["set"]:
        key = args["<key>"][0]
        assert key[-1] != "/", f'Key "{key}" should not end with a "/"!'
        url = args["<url>"]
        df = set_link(key, url, df)
        print_msg = f'Set key "{bolded(key)}" {bolded(ARROW)} "{bolded(url)}"'
        commit_msg = f'Set key "{key}" {ARROW} "{url}"'
    elif args["delete"]:
        keys = args["<key>"]
        poss = set(df.key)
        deletable = [k for k in keys if k in poss]
        df = delete_links(deletable, df)

        not_deletable = set(keys) - set(deletable)
        if not_deletable:
            msg = "Key{plural} {keys_pretty} not present..."
            pprint(plural_msg(not_deletable, msg))

        msg = "Deleted key{plural} {keys_pretty}"
        print_msg = plural_msg(deletable, msg, bold=True)
        commit_msg = plural_msg(deletable, msg, bold=False)

        if len(deletable) == 0:
            pprint("No keys to remove, exiting!")
            return
    elif args["hide"]:
        keys = args["<key>"]
        poss = set(df.key)
        hideable = [k for k in keys if k in poss]
        df = hide_links(hideable, df)

        not_hideable = set(keys) - set(hideable)
        if not_hideable:
            msg = "Key{plural} {keys_pretty} not present..."
            pprint(plural_msg(not_hideable, msg))

        msg = "(un)hid key{plural} {keys_pretty}"
        print_msg = plural_msg(hideable, msg, bold=True)
        commit_msg = plural_msg(hideable, msg, bold=False)

        if len(hideable) == 0:
            pprint("No keys to (un)hide, exiting!")
            return

    if args["cname"]:
        cname = args["<CNAME>"]
        set_state("CNAME", cname)
        print_msg = f"Set CNAME to {cname}."
        commit_msg = print_msg
    else:
        cname = None

    serialize_csv(df, csv_path)

    git_remote_url = repo.remotes.origin.url
    generate_pages(df, git_path, INDEX_NAME, get_state(), rurl=git_remote_url)

    try:
        pprint("Committing and pushing...")
        # presumably, this is a soft enforcement? I want links to not be cut off
        commit_push(repo, commit_msg)  # [:50]
        pprint(f'{bolded("Success")}: {print_msg}.')
    except Exception as e:
        reset_origin(repo)
        pprint(f"Failed; rolling back.")
        raise e


def main():
    if len(sys.argv) == 1:
        sys.argv.append("-h")

    args = docopt(__doc__)
    with ILock("golink"):
        execute(args)


if __name__ == "__main__":
    main()
