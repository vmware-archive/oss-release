#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Generate changelogs
===================

Based on https://github.com/tjstansell/salt-changelogs

This script accepts two git tags, and will build an RST changelog based on the
activity (pull requests merged, etc.) between those two tags.


REQUIREMENTS
------------

- Python 3
- A *NIX operating system
- git
- GitHub token

Go to https://github.com/settings/tokens/new to create a token. Give the token
a name, and check *only* the "public_repo" box, then scroll down and click
"Generate token". Make sure to copy the token as you only get to see it once.

Once you have the token, you can add it by running the script with the
``--add-token`` option, which will save it in a file within the cache dir (by
default ~/.cache/gen_changelog). Alternatively, if the CHANGELOG_GITHUB_TOKEN
environment variable is set, then its value will be used as the token in place
of whatever is present in the cache dir.


USAGE
-----

/path/to/gen_changelog.py --releases old new

Example: /path/to/gen_changelog.py --releases v2017.7.4 v2017.7.5

There are also a number of other command-line options, run the script with
``-h`` to see them.

NOTE: This script must be run from within the git repository for which you are
generating the changelog, unless you specify the path using the ``--repo``
option.

This will log to stderr and print the changelog to stdout, so it's a good idea
to use output redirection to write/append stdout to a file.

The data gathered for a given release will be cached to a JSON file in the data
dir. This allows the changelog to be generated more than once for the same
release without querying the GitHub API each time. To force the script to
gather the data again, use the ``--ignore-cache`` option. Note that this does
not prevent the script from saving the gathered data to the cache, it merely
keeps the script from considering cached data for the given release range when
building the changelog.

In addition to being used on the CLI, the Changelog class defined here can be
imported and used programmatically within other Python code.

CAVEATS
-------

- This script isn't perfect. It essentially spits out commit messages and
  sprinkles a little bit of RST fairy dust on them to make them look nice.
  Sometimes the text of the commit message contains characters that constitute
  invalid RST. After generating the changelog and adding it to the release
  notes, make sure to build the docs and look for warnings. Here are some
  common problems and the likely causes/solutions for them:

  - WARNING: Inline interpreted text or phrase reference start-string without
    end-string.

    - This is usually because a commit message contains a string which begins
      with a backtick and ends with a quote (usually a single-quote). Fix this
      by changing the backtick to a single-quote.

  - WARNING: Inline literal start-string without end-string.

    - This is likely caused when links are created from regex matches of a
      given issue number. This results in something like "``#2`_4927`_". In
      this particular case, the "#24927" issue number already had link markup
      added to it (resulting in "`#24927_`"), but the commit message ended in
      "#2…". The actual number was cut off with an ellipsis character and thus
      "#2" was matched and occurrences of "#2" had link markup added to them.
      The correct fix for this would be to remove the extra link markup,
      leaving it as "`#24927`_". Note that this particular case *should* be
      resolved now, but other cases may result in the same warning message.

  - WARNING: Inline emphasis start-string without end-string.

    - This is caused by an asterisk in the commit message. Fix this by escaping
      the asterisk with a backslash.

  - WARNING: Inline strong start-string without end-string.

    - This is caused by a double-asterisk in the commit message. Fix this by
      escaping both asterisks with backslashes.

  - WARNING: Unknown target name: somestring

    - This is caused by a trailing underscore on a word. You see this from time
      to time when a commit message refrences a function wich ends in an
      underscore (such as ones named with a trailing underscore to avoid
      shadowing built-ins). Fix this by escaping the underscore with a
      backslash.

- There is currently no way of logging to a file or file-like object when
  not running interactively. This is on the to-do list.

- There is no locking being done for the JSON cache file, so this script may
  produce unreliable results when being run more than once concurrently by the
  same user for the same release.
'''
import argparse
import datetime
import json
import logging
import os
import re
import sys
import subprocess
import urllib.error
import urllib.request

log = logging.getLogger()

_DEFAULTS = {
    'log_level': 'info',
    'log_format': '%(asctime)s [%(lineno)-3s][%(levelname)-5s] %(message)s',
    'cache_dir': '~/.cache/gen_changelog',
    'ignore_cache': False,
}

UNSUPPORTED_PYTHON = 1
INVALID_ARGS = 2
NO_TOKEN = 3
INVALID_TOKEN = 4
NO_REPORT = 5
KEYBOARD_INTERRUPT = 130


class JSONSetEncoder(json.JSONEncoder):
    '''
    Sets don't serialize, so convert them to lists. Sorting used to produce
    reliable results, as the order in which items are added to a set can affect
    its iteration order.
    '''
    def default(self, obj):
        if isinstance(obj, set):
            return sorted(obj)
        return super(JSONSetEncoder, self).default(obj)


class Changelog(object):

    issue_re = re.compile(r'((?:saltstack/[a-zA-Z0-9-]+#|#|bp-)(\d+))(…)?')
    user_re = re.compile(r'(\d+`_: \()(?:\*)([^*]+)(?:\*)(\))')
    token_re = re.compile('^[a-zA-Z0-9]+$')
    gh_datetime_format = '%Y-%m-%dT%H:%M:%SZ'
    report_datetime_format = '%Y-%m-%d %H:%M:%S UTC'

    def __init__(self,
                 old_release=None,
                 new_release=None,
                 repository=None,
                 log_level=_DEFAULTS['log_level'],
                 log_format=_DEFAULTS['log_format'],
                 cache_dir=_DEFAULTS['cache_dir'],
                 ignore_cache=_DEFAULTS['ignore_cache']):
        if sys.version_info[0] < 3:
            self.__exit(
                'This script will not run on Python {0}!'.format(sys.version[0]),
                UNSUPPORTED_PYTHON
            )
        elif old_release == new_release and old_release is not None:
            self.__exit('Old and new releases must be different!', INVALID_ARGS)

        self.__setup_logging(log_format, log_level)

        self.old_release = old_release
        self.new_release = new_release
        self.repository = self.__expand(repository) \
            if repository is not None \
            else os.getcwd()
        self.cache_dir = self.__expand(cache_dir)
        self.ignore_cache = ignore_cache

    def __str__(self):
        return self.__format_report()

    @staticmethod
    def __exit(msg, exit_status=0):
        '''
        Abort with a message and specific exit status
        '''
        if __name__ == '__main__':
            sys.stderr.write('\n{0}\n\n'.format(msg))
            sys.exit(exit_status)
        elif exit_status == 0:
            return True
        else:
            # Don't sys.exit if not being run interactively
            raise RuntimeError(msg)

    @staticmethod
    def __expand(path):
        return os.path.realpath(os.path.normpath(os.path.expanduser(path)))

    @staticmethod
    def __format_issue(issue_data, issue_id, formatted_refs=''):
        key = issue_id.lstrip('#')
        return '**{0}** {1}: (*{2}*) {3}{4}'.format(
            issue_data[key]['type'],
            issue_id if '#' in issue_id else '#' + issue_id,
            issue_data[key]['user']['login'],
            issue_data[key]['title'],
            formatted_refs)

    def __get_issue_data(self):
        '''
        Retrieve the issue data from the cache. If no cache match, or if
        --no-cache was used, then gather the information and save it to the
        cache before returning it.
        '''
        if not self.ignore_cache:
            try:
                cache = self.read_cache()
                ret = (
                    cache['timestamp'], cache['git_log_output'],
                    cache['issue_data'], cache['issue_revmap'],
                )
                log.debug('Using cached data for rev range %s', self.rev_range)
                return ret
            except KeyError:
                pass

        # Get current time to display in the report
        timestamp = datetime.datetime.utcnow().strftime(self.gh_datetime_format)

        # Get the issue numbers referenced in the commits within the rev range
        git_log_output = self.__run(
            ['git', 'log', '--graph', '--topo-order',
             '--oneline', '-s', self.rev_range])[0].splitlines()
        release_issues = set()
        for line in git_log_output:
            try:
                for issue_id, linked_issue, ellipsis in self.issue_re.findall(line):
                    # "issue_id" will contain the full match (e.g.
                    # saltstack/salt-jenkins#NNN, #NNNNN, bp-NNNNN), while
                    # "linked_issue" will contain just the numeric portion of
                    # the match.
                    if ellipsis:
                        # Prevent partial issue number matches ending in an
                        # ellipsis character from being added to issue data.
                        continue
                    release_issues.add(
                        issue_id if issue_id.startswith('saltstack/')
                        else linked_issue
                    )
            except AttributeError:
                # Line does not match
                pass

        # Query GitHub for all the issue data pertaining to the issue numbers
        # identified above.
        issue_data, issue_revmap = self.__query_issues(release_issues)

        self.write_cache({
            'timestamp': timestamp,
            'git_log_output': git_log_output,
            'issue_data': issue_data,
            'issue_revmap': issue_revmap,
        })

        return timestamp, git_log_output, issue_data, issue_revmap

    @staticmethod
    def __linkify(text):
        '''
        Wrap text in RST link markup
        '''
        return '`{0}`_'.format(text)

    def __make_cachedir(self):
        try:
            # Make the parent dir
            os.makedirs(self.cache_dir)
            log.debug('Made cache dir %s', self.cache_dir)
        except OSError as exc:
            if exc.errno != os.errno.EEXIST:
                self.__exit(
                    'Could not create {0}: {1}'.format(self.cache_dir, exc),
                    exc.errno
                )

    def __run(self, cmd):
        if self.repository is None:
            raise RuntimeError(
                'The {0} object\'s "repository" attribute must be set before '
                'attempting this action.'.format(self.__class__.__name__)
            )
        proc = subprocess.Popen(
            cmd,
            cwd=self.repository,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            # Add some handling when command fails
            log.error('Command %s failed: %s', cmd, stderr.decode())
            sys.exit(proc.returncode)
        return stdout.decode(), stderr.decode()

    @staticmethod
    def __setup_logging(log_format, log_level):
        '''
        Set log level/format based on what was specified on the CLI
        '''
        handler = logging.StreamHandler()  # Nothing special, logging to stderr
        handler.setFormatter(logging.Formatter(log_format))
        log.addHandler(handler)
        try:
            log_level = logging.getLevelName(log_level.upper())
            log.setLevel(log_level)
        except ValueError:
            # Invalid log level
            log.setLevel(logging.INFO)
            log.warning(
                'Invalid log level \'%s\', falling back to \'info\'',
                log_level
            )

    @staticmethod
    def __split_repo_and_issue(issue):
        try:
            repo, issue_num = issue.lstrip('#').split('#')
        except ValueError:
            repo = 'saltstack/salt'
            issue_num = issue
        return repo, issue_num

    def __query_github(self, issue):
        repo, issue_num = self.__split_repo_and_issue(issue)
        url = 'https://api.github.com/repos/{0}/issues/{1}'.format(repo, issue_num)
        req = urllib.request.Request(url)
        req.add_header('Authorization', 'token {0}'.format(self.token))
        log.debug('Querying GitHub issue %s', issue)
        try:
            with urllib.request.urlopen(req) as data:
                return json.loads(data.read().decode())
        except urllib.error.HTTPError as exc:
            log.error('Failed to read from %s: %s', url, exc)
            return None

    def __query_issues(self, issue_nums):
        '''
        Query the GitHub API for information on each specified issue, and all
        issues mentioned in the issue body.
        '''
        issue_data = {}
        issue_revmap = {}
        log.debug('Querying %d issues', len(issue_nums))

        def _gather(issue_nums, issue_data, issue_revmap):
            related = set()
            for issue_num in issue_nums:
                issue = self.__query_github(issue_num)
                if issue is None:
                    continue
                issue['type'] = 'PR' if 'pull_request' in issue else 'ISSUE'
                issue['description'] = '({0}) {1}'.format(issue['type'], issue['title'])

                if issue['type'] == 'PR':
                    log.debug('Searching body of PR %s for related issues', issue_num)
                    # Check PR body for linked issues
                    lines = [issue['title']]
                    lines.extend((issue['body'] or '').splitlines())
                    for line in lines:
                        for issue_id, linked_issue, ellipsis in self.issue_re.findall(line):
                            if ellipsis or '#' not in issue_id:
                                # The regex matched bp-NNNNN or fix-NNNNN,
                                # which we ignore here as we're only looking
                                # for linked issues.
                                continue
                            issue_id = issue_id.lstrip('#')
                            log.debug(
                                'Found related PR/issue %s in PR %s body',
                                issue_id, issue_num
                            )
                            issue.setdefault('related', set()).add(issue_id)
                            issue_revmap.setdefault(issue_id, set()).add(issue_num)
                            if not issue_id in issue_data:
                                # Only add to related if we havent gathered
                                # information for this issue yet, to prevent
                                # unnecessary duplicate API calls.
                                related.add(issue_id)

                issue_data[issue_num] = issue

            if related:
                log.debug('Recursing to query %d related issues', len(related))
                _gather(related, issue_data, issue_revmap)

        _gather(issue_nums, issue_data, issue_revmap)

        return issue_data, issue_revmap

    def __walk_issues(self, issues, to_walk):
        '''
        Get all issues related to each issue in to_walk
        '''
        walked = set()

        def _walk(to_walk, level=0):
            level += 1
            if level > 10:
                log.warning('walk_issues recursed more than 10 times')
                return

            related = set()
            for item in to_walk:
                if item in issues:
                    walked.add(item)
                    related.update(issues[item].get('related', []))

            # Prevents infinite recursion due issue referencing each other
            related -= walked
            if related:
                _walk(related, level)

        _walk(to_walk)
        buckets = {}
        for item in sorted(walked):
            buckets.setdefault(issues[item]['type'], []).append(item)

        return buckets.get('PR', []) + buckets.get('ISSUE', [])

    def __validate_token(self, token):
        '''
        Ensure that the token only contains hex characters
        '''
        if not self.token_re.match(token):
            self.__exit(
                'Token either empty or contains invalid characters!',
                INVALID_TOKEN
            )
        return token

    @property
    def cache_file(self):
        return os.path.join(self.cache_dir, '{0}.json'.format(self.rev_range))

    @property
    def rev_range(self):
        try:
            return '..'.join((self.old_release, self.new_release))
        except TypeError:
            raise RuntimeError(
                'The {0} object\'s "old_release" and "new_release" attributes '
                'must be set before attempting this action.'.format(
                    self.__class__.__name__
                )
            )

    @property
    def token_file(self):
        return os.path.join(self.cache_dir, 'token')

    @property
    def token(self):
        try:
            return self.__token
        except AttributeError:
            token = os.environ.get('CHANGELOG_GITHUB_TOKEN')
            if not token:
                try:
                    with open(self.token_file) as token_file:
                        token = token_file.read().strip()
                except OSError as exc:
                    self.__exit(
                        'Failed to read token file: {0}'.format(exc),
                        NO_TOKEN)
            self.__token = self.__validate_token(token)
            return self.__token

    def add_token(self, token=None):
        '''
        Writes the token to the cache dir. If a token is not provided, and we
        are running interactively, a token will be read from stdin.
        '''
        self.__make_cachedir()
        if token is None:
            if __name__ == '__main__':
                # Read token from stdin
                token = input('Input token: ').strip()
            else:
                self.__exit(
                    'Token must be provided when not being run interactively!',
                    NO_TOKEN
                )
        self.__validate_token(token)
        with open(self.token_file, 'w') as token_file:
            token_file.write('{0}\n'.format(token))
        msg = 'Wrote new token to {0}'.format(self.token_file)
        log.debug(msg)
        self.__exit(msg, exit_status=0)

    def read_cache(self):
        '''
        Read the issue cache
        '''
        log.debug('Reading cache file %s', self.cache_file)
        try:
            with open(self.cache_file) as cache_file:
                json_data = cache_file.read()
            return json.loads(json_data) if json_data else {}
        except OSError as exc:
            if exc.errno == os.errno.ENOENT:
                log.debug('Cache file %s does not exist', self.cache_file)
                return {}
            else:
                log.error(
                    'Failed to open %s for reading: %s', self.cache_file, exc)
        except TypeError as exc:
            log.error('Invalid filename %r for cache file', self.cache_file)
        except ValueError as exc:
            log.error('Failed to load JSON from %s: %s', self.cache_file, exc)
        return {'error': True}

    def write_cache(self, data):
        '''
        Write the issue cache
        '''
        self.__make_cachedir()
        try:
            log.debug('Writing cache to %s', self.cache_file)
            with open(self.cache_file, 'w') as cache_file:
                json.dump(
                    data,
                    cache_file,
                    ensure_ascii=False,
                    indent=4,
                    cls=JSONSetEncoder)
            return True
        except OSError:
            if exc.errno == os.errno.ENOTDIR:
                log.error(
                    'Parent of cache file %s is not a directory',
                    self.cache_file
                )
            else:
                log.error('Failed to open %s for writing: %s',
                          self.cache_file, exc)
            return False

    def build(self):
        '''
        Retrieve the issue data and use it to build the report
        '''
        timestamp, git_log_output, issue_data, issue_revmap = self.__get_issue_data()
        timestamp = datetime.datetime.strptime(timestamp, self.gh_datetime_format)

        self.merges = 0
        self.issues = 0
        self.pulls = 0
        result = []

        log.debug('Building report')
        for line in reversed(git_log_output):
            if 'Merge pull request' in line:
                self.merges += 1
                found_first_merge = True

            if not self.merges:
                # first few commits are actually part of merge, but do not show
                # that way in --graph view.  We fix that here.
                # * Merge ...      =>    * Merge ...
                # * commit 1       =>      * commit 1
                # * commit 2       =>      * commit 2
                line = '  ' + line

            try:
                # Search for data up until the commit ID
                prefix = re.match(r'^([^a-z0-9]+)', line).group(1)
            except AttributeError:
                prefix = ''
            else:
                # Remove graph data from beginning of line
                line = line[len(prefix):]
                # Remove everything after *, and add a space after.
                prefix = re.sub(r'\*.*', '* ', prefix, count=1)
                # Now convert everything that isn't an asterisk to a space. We now
                # have an asterisk at the proper indentation level.
                prefix = re.sub(r'[^*]', ' ', prefix)
                # Rewrite line with indentation and prefix
                line = '  ' + prefix + line
                # Make prefix into a blank string of the same length
                prefix = ' ' * len(prefix)

            line_issues = set(x[1] for x in self.issue_re.findall(line))

            if line.startswith('  * '):
                content = line[4:]
                try:
                    issue_num = re.search(r'pull request #(\d{5})', content).group(1)
                except AttributeError:
                    issue_num = ''
                else:
                    result.extend([line, ''])

                refs = self.__walk_issues(
                    issue_data,
                    [x[1] for x in self.issue_re.findall(line)])
                if issue_num and issue_num not in refs:
                    refs.append(issue_num)

                for ref in refs:
                    prefix = '' \
                        if ref == issue_num \
                            or issue_data.get(ref, {}).get('type') == 'ISSUE' \
                        else '  '
                    if ref == issue_num:
                        # Add line noting when merged if this info is present
                        try:
                            closed_at = datetime.datetime.strptime(
                                issue_data[ref]['closed_at'],
                                self.gh_datetime_format)
                        except (KeyError, ValueError):
                            pass
                        else:
                            result.append(
                                '{0}  @ *{1}*'.format(
                                    prefix,
                                    closed_at.strftime(self.report_datetime_format)
                                )
                            )

                    # Add any refs (fix this shit, maybe move to previous line of
                    # output)
                    try:
                        formatted_refs = (
                            ' (refs: {0})'.format(
                                ', '.join(
                                    ['#{0}'.format(x) for x in issue_revmap[ref]]
                                )
                            )
                        )
                    except KeyError:
                        formatted_refs = ''

                    # Format the line
                    formatted = self.__format_issue(issue_data, ref, formatted_refs)
                    if 'ISSUE' in formatted:
                        self.issues += 1
                    elif 'PR' in formatted:
                        self.pulls += 1
                    result.extend(['* '.join((prefix, formatted)), ''])

            elif '*' in line:
                result.extend([line[2:], ''])

        # We built the report from the bottom up to ensure we linked all
        # information
        links = set()
        contributors = set()

        # Build all the RST link targets and rewrite the issue numbers as links
        for idx, line in enumerate(result):

            # Create links for issue numbers
            for issue_id, issue_num, ellipsis in set(self.issue_re.findall(line)):
                key = issue_id.lstrip('#')
                if ellipsis or '#' not in issue_id or key not in issue_data:
                    continue
                link_text = self.__linkify(issue_id)
                line = line.replace(issue_id, link_text).replace('\\', '\\\\')

                link_target = 'https://github.com/{0}/{1}/{2}'.format(
                    self.__split_repo_and_issue(issue_id)[0],
                    'pull' if issue_data[key]['type'] == 'PR' else 'issues',
                    issue_num
                )
                links.add(
                    '.. _`{0}`: {1}'.format(issue_id, link_target)
                )

            # Create link for GitHub username
            try:
                github_user = self.user_re.search(line).group(2)
                if '**PR**' in line:
                    contributors.add(github_user)
            except AttributeError:
                pass
            else:
                line = self.user_re.sub(r'\1' + '`' + r'\2' + '`_' + r'\3', line)
                link_target = 'https://github.com/{0}'.format(github_user)
                links.add(
                    '.. _`{0}`: {1}'.format(github_user, link_target)
                )

            if line != result[idx]:
                # Changes were made to the line, so replace it
                result[idx] = line


        report = []
        report.extend(['Statistics',
                       '==========',
                       ''])
        report.append('- Total Merges: **{0}**'.format(self.merges))
        report.append('- Total Issue References: **{0}**'.format(self.issues))
        report.extend(['- Total PR References: **{0}**'.format(self.pulls), ''])
        contributor_line = '- Contributors: **{0}** ({1})'.format(
            len(contributors),
            ', '.join((self.__linkify(x) for x in sorted(contributors)))
        )
        report.extend([contributor_line,
                       '',
                       '',
                       'INSERT RELEASE NOTES BODY HERE',
                       '',
                       ''])

        changes_line = 'Changelog for {0}'.format(self.rev_range)
        report.append(changes_line)
        report.extend(['=' * len(changes_line), ''])
        report.append(
            '*Generated at: {0}*'.format(
                timestamp.strftime(self.report_datetime_format)
            )
        )

        # If commits were added but not associated with a PR (sometimes happens
        # right as we are tagging a release) then the first couple commits in
        # the log output will be indented. remove the indentation for those
        # lines.
        first_issue_index = -1
        for line in reversed(result):
            if line.startswith('*'):
                break
            first_issue_index -= 1
        report.extend((x.lstrip() for x in result[-1:first_issue_index:-1]))

        # Now add any remaining lines
        report.extend(result[first_issue_index::-1])

        if links:
            report.append('')
            report.extend(sorted(links))

        # Ensure report ends in newline
        report.append('')

        return '\n'.join(report)


def __parse_args():
    '''
    Parse CLI input
    '''
    parser = argparse.ArgumentParser(
        description='Identify PRs/issues from the git log, then gather '
                    'info on them using the GitHub API. Use the resulting '
                    'data to build an RST changelog.'
    )
    runtime_opts = parser.add_mutually_exclusive_group(required=True)
    runtime_opts.add_argument(
        '--add-token',
        dest='token',
        nargs='?',
        help='Add a GitHub token, or replace existing token. If token is not '
             'provided on the CLI, it will be read from stdin.',
        metavar='token',
        default=False)
    runtime_opts.add_argument(
        '--releases',
        metavar='<tag>',
        nargs=2,
        help='Tags for the old and new releases')

    parser.add_argument(
        '--repo', '--repository',
        dest='repository',
        help='Path to the repository (defaults to cwd)',
        default=None)

    log_opts = parser.add_argument_group('logging')
    log_opts.add_argument(
        '-l', '--log-level',
        help='Set the log level (default: %(default)s)',
        metavar='level',
        default=_DEFAULTS['log_level'])
    log_opts.add_argument(
        '--log-format',
        help='Set the format for log messages',
        metavar='format',
        default=_DEFAULTS['log_format'])
    cache_opts = parser.add_argument_group('cache')
    cache_opts.add_argument(
        '--cache-dir',
        help='Path to cache dir (default: %(default)s)',
        default=_DEFAULTS['cache_dir'])
    cache_opts.add_argument(
        '--ignore-cache',
        action='store_true',
        help='Re-query all issues (do not use cached data)')
    return parser.parse_args()


if __name__ == '__main__':
    opts = __parse_args()

    try:
        old_release, new_release = opts.releases
    except (TypeError, ValueError):
        # --add-token was passed on the CLI
        old_release = new_release = None

    changelog = Changelog(
        old_release,
        new_release,
        repository=opts.repository,
        log_level=opts.log_level,
        log_format=opts.log_format,
        cache_dir=opts.cache_dir,
        ignore_cache=opts.ignore_cache)

    if opts.token is not False:
        changelog.add_token(opts.token)
    else:
        try:
            sys.stdout.write(changelog.build())
        except OSError:
            # If output was piped to a pager then stdout will be closed by the
            # time the pager exists. This squelches the resulting traceback.
            pass
