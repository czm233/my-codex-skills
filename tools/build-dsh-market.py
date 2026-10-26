#!/usr/bin/env python3
"""Build a DSH market index pinned to an existing Git revision; no network or writes."""
import argparse
import json
import subprocess
from urllib.parse import urlsplit

parser = argparse.ArgumentParser()
parser.add_argument('--repository', required=True, help='Public HTTPS Git repository URL')
parser.add_argument('--revision', default='HEAD')
args = parser.parse_args()
url = urlsplit(args.repository)
if url.scheme != 'https' or not url.netloc or url.username or url.password or url.query or url.fragment:
    parser.error('repository must be an HTTPS URL without credentials, query or fragment')

def git(*command):
    return subprocess.check_output(['git', *command], text=True).strip()

commit = git('rev-parse', '--verify', args.revision + '^{commit}')
path = 'plugins/bark-notifications'
package = json.loads(git('show', f'{commit}:{path}/package.json'))
if not package.get('dsh', {}).get('bundle'):
    parser.error('selected revision does not contain the DSH bundle')
index = {
    'format': 1,
    'title': {'en': 'My plugins', 'zh': '我的插件'},
    'plugins': [{
        'name': package['name'],
        'title': 'Bark Notifications',
        'description': {'en': 'Bark notifications after each Harness turn.', 'zh': 'Harness 每轮回复结束后发送 Bark 通知。'},
        'repository': {'url': args.repository},
        'versions': [{
            'version': package['version'],
            'publishTimestamp': int(git('show', '-s', '--format=%ct', commit)),
            'source': {'type': 'git', 'url': args.repository, 'commit': commit, 'path': path},
        }],
    }],
}
print(json.dumps(index, ensure_ascii=False, indent=2))
