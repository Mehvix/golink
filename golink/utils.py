import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import git
import pandas as pd
import requests
from git import RemoteProgress
from git.repo import Repo

ARROW = "⇒"
DEFAULT_PROTECTED = [".git", "CNAME"]
# GA = """
# <!-- Google Analytics -->
# <script>
# (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
# (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
# m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
# })(window,document,'script','https://www.google-analytics.com/analytics.js','ga');
# """
# TODO Google is evil; find a viable alternative. Count how many times link is clicked + display


def try_state(git_path, meta_name):
    p = Path(git_path / meta_name)
    return json.load(open(p, "r"))


def pprint(x):
    msg = bolded("=> ") + x
    print(msg)


def bolded(x):
    return "\033[1m" + x + "\033[0m"


def empty_csv():
    return pd.DataFrame({
        'date':[],
        'key':[],
        'url':[],
        'hide':[]
    })

def serialize_csv(df, path):
    df.to_csv(str(path), index=False)


def load_csv(f):
    return pd.read_csv(str(f))


class CloneProgress(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=""):
        if message:
            print(message)
        return super().update(op_code, cur_count, max_count, message)


def clone(url, path: Path) -> Repo:
    prog = CloneProgress()
    return Repo.clone_from(url, path, progress=prog)


def commit_push(repo, commit_msg):
    repo.git.add(all=True)
    repo.index.commit(commit_msg)
    origin = repo.remote(name="origin")
    origin.push()


def clean(repo):
    repo.git.clean("-xdf")


def check_repo(repo, index_name):
    wd = repo.working_dir
    try:
        load_csv(str(Path(wd) / index_name))
        return True
    except:
        return False


def wipe_directory(dired, protected):
    protected = set(protected + DEFAULT_PROTECTED)
    for child in dired.iterdir():
        not_protected = child.name not in protected
        is_dir = child.is_dir()
        is_index = child.name == "index.html"
        if not_protected and (is_dir or is_index):
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()


def try_setup(repo: Repo, path: Path, index_name, state_name):
    # path is the path of a git repository
    # Clean up any non-tracked changes
    # Then check if there's an index.csv; if so, exit
    # If no index.csv, delete everything in repo, make an empty index.csv
    clean(repo)
    index_path = path / index_name
    state_path = path / state_name

    if not check_repo(repo, index_name):
        pprint("Not a valid repo; reinitializing.")
        # delete everything in directory
        wipe_directory(path, [".git"])

        empty = empty_csv()
        serialize_csv(empty, index_path)
        with open(state_path, "w+") as fout:
            json.dump({}, fout)

        try:
            commit_push(repo, "Initialization")
        except Exception as e:
            pprint("Remote update failed; try initializing again!")
            raise e


def template_maker(url):
    return f'<meta http-equiv="refresh" content="0; URL={url}"/>'


def prettify_list(ls, bold=True):
    if bold:
        func = lambda x: f'"{bolded(x)}"'
    else:
        func = lambda x: f'"{x}"'

    return ", ".join(map(func, ls))


def generate_pages(df, working_dir, index_name, state, rurl=None):
    wd = Path(working_dir)
    if "CNAME" in state:
        cname = state["CNAME"]
        with open(wd / cname, "w+") as f:
            f.write(cname)
    # if 'GA Property ID' in state:
    #     prop_id = state['GA Property ID']
    # else:
    #     prop_id = None

    protected = [".git", index_name]
    wipe_directory(wd, protected)

    pprint("Rebuilding HTML...")
    iterator = df.sort_values("key").iterrows()
    inner_list = []
    for _, row in iterator:
        key, url, hide, date = row.key, row.url, row.hide, row.date
        html_file = wd / (key + "/index.html")
        parent = html_file.parent
        parent.mkdir(exist_ok=True, parents=True)

        with open(html_file, "w+") as f:
            f.write(template_maker(url))
        if not hide:
            inner_list.append(
                f'<tr><td>{date}</td><td><a href="{key}">{key}</a></td><td>{ARROW}</td><td><a href="{url}">{url}</a></td></li>\n'
            )

    current_file_path = Path(__file__)
    package_path = current_file_path.parent

    css_file = package_path / "style.css"
    assert css_file.is_file()
    css_txt = css_file.read_text()

    js_file = package_path / "script.js"
    assert js_file.is_file()
    js_txt = js_file.read_text()

    # hacky
    parse_rurl = lambda x: x.replace("git@github.com:", "https://github.com/")[:-4]

    with open(wd / "index.html", "w+") as index_file:
        html = f"""
<title>golink</title>
<style>{css_txt}</style>
<header>
<span>
<h1><a class="rem" href='https://github.com/Mehvix/golink'>golink</a></h1>
{"" if rurl is None else f'<a class="rem" href="{parse_rurl(rurl)}">remote</a>'}
</span>
<div><input type="checkbox" class="btn-toggle" id="toggle"><label for="toggle"><i></i></label></div>
</header>
<table><tbody>
<tr><th>Date Updated</th><th>Key</th><th></th><th>URL</th></tr>
{"".join((inner_list))}
</tbody></table>
<script>{js_txt}</script>"""
        # if prop_id:
        #     html = html + GA.format(prop_id)

        index_file.write(html)


def url_exists(url):
    try:
        request = requests.get(url, timeout=0.5)
        return True
    except:
        return False


def plural_msg(ls, fmt_str, bold=True):
    plural = "s" if len(ls) > 1 else ""
    keys_pretty = prettify_list(ls, bold=bold)
    return fmt_str.format(plural=plural, keys_pretty=keys_pretty)


def reset_origin(repo):
    repo.git.reset("--hard", f"origin/{repo.active_branch}")


def patch_url(url):
    if url[:4] == "http":
        return url
    else:
        if url_exists("https://" + url):
            protocol = "https://"
        elif url_exists("http://" + url):
            protocol = "http://"
        else:
            protocol = None

        if protocol:
            patched = f"{protocol}{url}"
            pprint(f'No schema given for "{url}"! Patching to "{patched}"...')
            return patched
        else:
            pprint(f'No schema given for URL "{url}"!')
            msg = f'No valid schema for given URL! Did you mean "http://{url}"?'
            raise ValueError(msg)


# This is from StackOverflow.
def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' \n"
                             "(or 'y' or 'n').\n")
