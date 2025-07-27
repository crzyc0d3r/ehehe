import subprocess
import json
import re

def get_metrics(merges=False):
    flag = '--merges' if merges else '--no-merges'
    log = subprocess.check_output(
        ['git', '-c', 'i18n.logoutputencoding=utf8', 'log', flag, '--numstat', '--pretty=format:%H%n%aN%n%b']
    ).decode('utf-8', errors='ignore')
    
    metrics = {}
    current_author = None
    current_body = ""
    current_hash = None
    
    lines = log.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line and re.match(r'^[a-f0-9]{40}$', line):  # Commit hash
            # Process previous commit if exists
            if current_author:
                if merges:
                    co_authors = re.findall(r'Co-authored-by:\s*(.+?)\s*<', current_body, re.IGNORECASE)
                    for co_author in co_authors:
                        if co_author not in metrics:
                            metrics[co_author] = {'commits': 0, 'added': 0, 'removed': 0}
                        metrics[co_author]['commits'] += 1
                else:
                    if current_author not in metrics:
                        metrics[current_author] = {'commits': 0, 'added': 0, 'removed': 0}
                    metrics[current_author]['commits'] += 1
            
            current_hash = line
            i += 1
            if i < len(lines):
                current_author = lines[i].strip()
                i += 1
            current_body = ""
        else:
            if current_author:
                if '\t' in line and re.match(r'^\d+\t\d+\t', line):
                    parts = line.split('\t')
                    if len(parts) == 3:
                        added = int(parts[0])
                        removed = int(parts[1])
                        if merges and 'Co-authored-by' in current_body:
                            co_authors = re.findall(r'Co-authored-by:\s*(.+?)\s*<', current_body, re.IGNORECASE)
                            for co_author in co_authors:
                                if co_author not in metrics:
                                    metrics[co_author] = {'commits': 0, 'added': 0, 'removed': 0}
                                metrics[co_author]['added'] += added
                                metrics[co_author]['removed'] += removed
                        else:
                            if current_author not in metrics:
                                metrics[current_author] = {'commits': 0, 'added': 0, 'removed': 0}
                            metrics[current_author]['added'] += added
                            metrics[current_author]['removed'] += removed
                else:
                    current_body += line + "\n"
            i += 1
    
    # Process the last commit
    if current_author:
        if merges:
            co_authors = re.findall(r'Co-authored-by:\s*(.+?)\s*<', current_body, re.IGNORECASE)
            for co_author in co_authors:
                if co_author not in metrics:
                    metrics[co_author] = {'commits': 0, 'added': 0, 'removed': 0}
                metrics[co_author]['commits'] += 1
        else:
            if current_author not in metrics:
                metrics[current_author] = {'commits': 0, 'added': 0, 'removed': 0}
            metrics[current_author]['commits'] += 1

    result = {}
    for author, data in metrics.items():
        count = data['commits']
        added = data['added']
        removed = data['removed']
        score = (count * 0.4) + (added * 0.3) + (removed * 0.2)
        result[author] = {'commits': count, 'added': added, 'removed': removed, 'score': score}
    
    return result

# Run in repo directory
non_merge = get_metrics(merges=False)
merge = get_metrics(merges=True)

combined = {}
all_users = set(non_merge.keys()) | set(merge.keys())
for user in all_users:
    combined[user] = {
        'non_merge': non_merge.get(user, {'commits': 0, 'added': 0, 'removed': 0, 'score': 0.0}),
        'merge': merge.get(user, {'commits': 0, 'added': 0, 'removed': 0, 'score': 0.0})
    }

with open('user_metrics.json', 'w', encoding='utf-8') as f:
    json.dump(combined, f, indent=4)