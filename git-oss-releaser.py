#!/usr/bin/env python3
from io import StringIO
from tempfile import NamedTemporaryFile

import argparse
import logging
import os
import re
import shutil
import subprocess
import sys

logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument("repoDir", help="The repository to transform. May also be a subdirectory of a repo.")
parser.add_argument("outDir", help="The directory where the new repo should be created. Has to be empty.")
parser.add_argument("--name", help="The user.name to use for committing the files. Defaults to git's global user.name", default=None)
parser.add_argument("--email", help="The user.email to use for committing the files. Defaults to git's global user.email", default=None)
parser.add_argument("--date", help="The date to use for commits. Defaults to the date  the last commit.", default=None)
args = parser.parse_args()

repoDir = os.path.abspath(args.repoDir)
outDir = os.path.abspath(args.outDir)
committerName = args.name
committerEmail = args.email
forcedCommitDate = args.date

finalRepoDir = os.path.join(outDir, "res")
firstAuthor = "git-oss-releaser <>"
firstCommitMessage = "Initializes text files"
commitMessagePattern = "Contribution by {}"

authorDirPattern = "V{0:05d}"
authorFilenamePattern = authorDirPattern + ".author"

lastAuthorNum = 0
commitDate = "0"

def create_authors_file(author):
    #write to authorFile to enable manual git commits
    authorFilename = authorFilenamePattern.format(lastAuthorNum)
    target = os.path.join(outDir, authorFilename);
    authorFile = open(target, 'w')
    authorFile.write(author)
    authorFile.close()

def ensure_parentdir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)

blamelinepattern = re.compile('([\d\w]+)\t\(([^\t]+)\t([^\t]+)\t\d+\)(.*)')

authorIDs = {} # hash from authorID to num
authorNums = {} # hash from numbers to full commit strings
fullAuthors = {} # hash from full id to number, required for binary files
hasContributed = set() # not all authors might have contributed to the last version, therefore we track them

#copied from http://stackoverflow.com/a/7420617/873282
def move_dir1_into_dir2(root_src_dir, root_dst_dir):
    for src_dir, dirs, files in os.walk(root_src_dir):
        dst_dir = src_dir.replace(root_src_dir, root_dst_dir)
        if not os.path.exists(dst_dir):
            os.mkdir(dst_dir)
        for file_ in files:
            src_file = os.path.join(src_dir, file_)
            dst_file = os.path.join(dst_dir, file_)
            if os.path.exists(dst_file):
                os.remove(dst_file)
            shutil.move(src_file, dst_dir)

def git_add_everything():
    subprocess.check_call("git add -A", shell=True)

def git_commit(message, author):
    subprocess.check_call("git commit" +
                          " -m\"" + message + "\"" +
                          " --author=\"" + author + "\"" +
                          " --date=\"" + commitDate + "\"",
                          shell=True)
 
def prepare_release():
    #prepare things prone to errors before the actual conversion
    if os.path.exists(finalRepoDir):
        shutil.rmtree(finalRepoDir)
    os.makedirs(finalRepoDir)

    for i in range(0, lastAuthorNum+1):
        dirName = authorDirPattern.format(i)
        authorDir = os.path.join(outDir, dirName)
        if os.path.exists(authorDir):
            shutil.rmtree(authorDir)
        else:
            break

    os.chdir(finalRepoDir)
    subprocess.check_call("git init", shell=True)
    if committerName != None:
        subprocess.check_call("git config user.name \"" + committerName + "\"", shell=True)
    if committerEmail != None:
        subprocess.check_call("git config user.email \"" + committerEmail + "\"", shell=True)
    

# prepare_release() has to have been called before callling this function
def do_release():
    global commitDate
    if forcedCommitDate != None:
        commitDate = forcedCommitDate

    logging.info("Adding to release git repository...")

    os.chdir(finalRepoDir)

    dirName = authorDirPattern.format(0)
    source = os.path.join(outDir, dirName)
    move_dir1_into_dir2(source, finalRepoDir)
    git_add_everything()
    git_commit(firstCommitMessage, firstAuthor)

    for contributor in sorted(hasContributed):
        dirName = authorDirPattern.format(contributor)
        source = os.path.join(outDir, dirName)
        move_dir1_into_dir2(source, finalRepoDir)
        git_add_everything()
        author = authorNums[contributor]
        pos = author.find('\n')
        author = author[0:pos]
        pos = author.find(' <')
        authorName = author[0:pos]
        message = commitMessagePattern.format(authorName)
        git_commit(message, author)

def determineAllAuthors():
    global lastAuthorNum
    global fullAuthors
    global authorNums

    allAuthors = subprocess.check_output("git log --format=\"%an <%ae>\"", shell=True, universal_newlines=True)
    for line in StringIO(allAuthors):
        if (line not in fullAuthors):
            logging.debug("found author %s", line)
            lastAuthorNum += 1
            create_authors_file(line)
            fullAuthors[line] = lastAuthorNum
            authorNums[lastAuthorNum] = line

    logging.debug("%s authors in total", lastAuthorNum)

#curFileName has to be relative to the sourcedir
def workOnFile(curFileName):
    logging.debug("Working on %s...", curFileName)
    global hasContributed
    global commitDate

    binary = subprocess.check_output("git diff --numstat 4b825dc642cb6eb9a060e54bf8d69288fbee4904 HEAD -- \"" + curFileName + "\"", shell=True)
    if binary[0:1] == b'-':
        #binary found
        logging.debug("handling as binary")

        #just assign it to the last commiter ("-1") of the binary file
        cmd = "git log --format=\"%an <%ae>\" -1 -- \"" + curFileName + "\""
        author = subprocess.check_output(cmd, shell=True).decode("utf-8")
        authorNum = fullAuthors[author]
        hasContributed.add(authorNum)

        for i in range(authorNum, lastAuthorNum+1):
            dirName = authorDirPattern.format(i)
            target = os.path.join(outDir, dirName, curFileName)
            ensure_parentdir(target)
            shutil.copy(curFileName, target)

    else:
        #text file
        logging.debug("handling as text")

        #handle using output of git blame -c

        #prepare targetfiles
        targetFiles = {}
        for i in range(0, lastAuthorNum+1):
            #loop starts from 0 as V0 is the version containing blank lines only. This ensures that the first author does not play a special role (git treats V0 as the author creating the files, all others have changed lines only)
            dirName = authorDirPattern.format(i)
            target = os.path.join(outDir, dirName, curFileName)
            ensure_parentdir(target)
            targetFiles[i] = {}
            targetFiles[i]['handle'] = open(target, 'w') # w ensures overwriting of files created in previous runs
            targetFiles[i]['name'] = target

        #HEAD is needed to avoid scenario described at http://stackoverflow.com/questions/4638500/git-blame-showing-no-history
        output = subprocess.check_output("git blame -c HEAD \"" + curFileName + "\"", shell=True, universal_newlines = True)
        res = StringIO(output)

        for line in res:
            #logging.debug("line: %s", repr(line))

            m = blamelinepattern.match(line)
            commitID = m.group(1)
            authorID = m.group(2)
            date = m.group(3)
            content = m.group(4)

            #logging.debug("commitID: %s", commitID)
            #logging.debug("authorID: %s", authorID)
            #logging.debug("date: %s", date)
            #logging.debug("content: %s", content)

            if (date > commitDate):
                commitDate = date

            #get author
            #we assume that the authorID is unique
            if authorID in authorIDs:
                authorNum = authorIDs[authorID]
            else:
                #if no committer has been found, add to mapping from id to number
                author = subprocess.check_output("git --no-pager show -s --format=\"%an <%ae>\" " + commitID, shell=True).decode("utf-8")
                authorNum = fullAuthors[author]
                authorIDs[authorID] = authorNum

            hasContributed.add(authorNum)

            #content (without newline) is assigned to author only
            #authors after the current one get the content nevertheless: this ensures a proper handling by git
            for i in range(0, authorNum):
                targetFiles[i]['handle'].write("\n")
            for i in range(authorNum, lastAuthorNum+1):
                targetFiles[i]['handle'].write(content)
                targetFiles[i]['handle'].write("\n")

        for targetFile in targetFiles.values():
            targetFile['handle'].close()

logging.info("Preparing analysis...")

prepare_release()
os.chdir(repoDir)

os.chdir(repoDir)
determineAllAuthors()

logging.info("Preparing templates...")
 
#does not work if filenames contain en dash (u2013).
#solution posted at http://stackoverflow.com/a/6007172/873282 does not work at Python 3.5 
for dirpath, dirnames, filenames in os.walk(repoDir):
    #ignore .git directory
    if '.git' in dirnames:
        dirnames.remove('.git')
    for filename in filenames:
        relPath = os.path.join(dirpath[len(repoDir)+1:], filename)
        workOnFile(relPath)

do_release()
