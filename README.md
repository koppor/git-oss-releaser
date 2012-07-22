About
-----
git-oss-releaser converts a given git repostiory to a git repostory only containing the files of the last commit and commits resembling `git blame` output for each files. The original history is lost.

The motivation is privacy of the developers involved. For instance, code comments made in rage during development should not be made public.

git-oss-releaser is written using Python 3.

A discussion about this feature is made at [stackoverflow](http://stackoverflow.com/questions/11482925/automatically-rewrite-git-history-for-open-source-release).


Usage
-----
usage: `git-oss-releaser.py [-h] repoDir outDir`

Positional arguments:

 * `repoDir`: The repository to transform. May also be a subdirectory of a repo.
 * `outDir`: The directory where the new repo should be created. Has to be empty.

optional arguments

 * `--name NAME`    The user.name to use for committing the files. Defaults to git's global user.name
 * `--email EMAIL`  The user.email to use for committing the files. Defaults to git's global user.email
 * `--date DATE`    The date to use for commits. Defaults to the date the last commit.

DEBUG mode can currently only be enabled in the code.


Limitations
-----------
 * works only on git repositories without any untracked files.
 * empty lines are assigned to "git-oss-releaser" and not the first or last author adding these empty lines
 * repository has to contain at least one non-binary file
 * commit date is derived from non-binary files only
 * Tested under [msysGit](http://msysgit.github.com/) only.

