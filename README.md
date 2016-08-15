# GIT Open Source Releaser

## About
git-oss-releaser converts a given git repository to a git repository only containing the files of the last commit and commits resembling `git blame` output for each file.
The original history is lost.

The motivation is privacy of the developers involved. For instance, code comments made in range during development should not be made public.

git-oss-releaser is written using [Python 3](https://www.python.org/downloads/) and requires at least Python 3.5.

A discussion about this feature is made at [stackoverflow](http://stackoverflow.com/questions/11482925/automatically-rewrite-git-history-for-open-source-release).


## Example

GIT OSS releaser has been used in the context of the [awesome-bpm list](https://github.com/ungerts/awesome-bpm/).
The [commits](https://github.com/ungerts/awesome-bpm/commits/master) from Dec 16, 2015 present the results of the application.


## Usage
usage: `git-oss-releaser.py [-h] repoDir outDir`

Positional arguments:

 * `repoDir`: The repository to transform. May also be a subdirectory of a repo.
 * `outDir`: The directory where the new repo should be created. Has to be empty.

Optional arguments:

 * `--name NAME`    The `user.name` to use for *committing* the files. Defaults to git's global `user.name`.
 * `--email EMAIL`  The `user.email` to use for *committing* the files. Defaults to git's global `user.email`.
 * `--date DATE`    The date to use for commits. Defaults to the date the last commit.

Note that git distinguishes author and committer at a commit.
The author is taken using `git blame`, the committer data is taken from the global `user.name` and `user.email`or the given configured `--name` and `--email`.

DEBUG mode can currently only be enabled in the code.


## Limitations

 * Works on git repositories without any untracked files only
 * Empty lines are assigned to "git-oss-releaser" and not the first or last author adding these empty lines
 * Repository has to contain at least one non-binary file
 * Commit date is derived from non-binary files only
 * Tested under [git for windows](https://git-for-windows.github.io/) only
