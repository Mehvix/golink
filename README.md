# `golink` - git powered go-links
<p align = 'center'>
    Host your own "<a href="https://yiou.me/blog/posts/google-go-link">go-links</a>" via git and <a href="https://pages.github.com">github pages</a>
    <br/>
    <code>pip install golink</code>
    <br/>
    <p align = 'center'>
    <img src="https://raw.githubusercontent.com/Mehvix/golink/master/.github/assets/demo.gif"/>
    </p>
</p>


**What:** `golink` is a command line tool that maps custom shortlinks to URLs via
[Git](https://git-scm.com) and [GitHub Pages](https://pages.github.com). This free software is licensed under GPLv3 and is a fork of [gitlink](https://github.com/lengstrom/gitlinks).


**How:** `golink` works by [storing state on GitHub](https://github.com/lengstrom/goto/blob/main/index.csv)
and [rendering structured redirects on GitHub pages](https://github.com/lengstrom/goto). Add, remove, and visualize link mappings through the command line!


## Commands
```
$ golink set zoom https://mit.zoom.us/j/95091088705
  => Success: Set key "zoom" → "https://mit.zoom.us/j/95091088705".
```
```
$ golink hide zoom
  => Success: Removed key "zoom".
```
```
$ golink show
=> Checking for changes from remote...
== golink (Remote: git@github.com:lengstrom/goto.git) ==
calendly                 →   https://calendly.com/loganengstrom
classes/18.102           →   http://math.mit.edu/~rbm/18-102-S17/
classes/6.005            →   http://web.mit.edu/6.031/www/fa18/general/
ffcv_slack               →   https://ffcv-workspace.slack.com/join/shared_invite/zt-11olgvyfl-dfFerPxlm6WtmlgdMuw_2A#/shared-invite/email
papers/bugsnotfeatures   →   https://arxiv.org/abs/1905.02175
zombocom                 →   https://www.zombo.com
zoom                     →   https://mit.zoom.us/j/95091088705c
```
<!-- TODO upd this output, and gif -->


# Setup

Configure `golink` in two steps!

## Set-up GitHub Repository

First, visit https://github.com/new and choose a short, memorable name like `go` for your golink repository.

<!-- . -->
![](https://raw.githubusercontent.com/Mehvix/golink/master/.github/assets/make_repo.png)

Now, check the box "Add a README file" (the repository can't be empty).

![](https://raw.githubusercontent.com/Mehvix/golink/master/.github/assets/add_readme.png)

Make the repository, then go your repository's GitHub pages settings: `https://github.com/<USERNAME>/go/settings/pages` and **enable GitHub pages** for the `master`/`main` branch:

![](https://raw.githubusercontent.com/Mehvix/golink/master/.github/assets/enable_ghpages.png)

## Install `golink`

### pip

```sh
pip install golink
```

### [pipx](https://pypa.github.io/pipx/)

```sh
git clone https://github.com/Mehvix/golink.git
cd golink
pipx install .
```

## Initialize `golink`


```sh
golink init <remote_url>
```

Your `<remote_url>` can be found here:

![](https://raw.githubusercontent.com/Mehvix/golink/master/.github/assets/remote_url.png)

---

After this step, you should be able to make go-links to your heart's content.


# todos

- [x] Dark theme (OneDark?)
- [x] Migration CLI function
- [ ] Faster forwarding?
- [ ] Proper arg parsing
- [ ] Mobile support
- [ ] Silly header
- [ ] Forward link metadata
