# -*- coding: utf-8 -*-
# resources/lib/zachmorris_repo_installer.py
import re
from resources.lib.repo_installer import install_github_release

def download_zachmorris_repo():
    return install_github_release(
        source_predicate=lambda s: 'zach morris' in s.get('name', '').lower(),
        repo_path_extractor=lambda url: re.search(r'https://github.com/([^/]+/[^/]+)', url).group(1),
        asset_filter=lambda name: name.lower().startswith('repository.zachmorris') and name.lower().endswith('.zip'),
        addon_name='Zach Morris Repo'
    )
