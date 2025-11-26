# -*- coding: utf-8 -*-
# resources/lib/zachmorris_repo_installer.py
from resources.lib.repo_installer import install_github_release

def download_zachmorris_repo():
    return install_github_release(
        source_predicate=lambda s: any(word in s.get('name', '').lower() for word in ['zachmorris', 'zach morris', 'zach-morris']),
        repo_path_extractor=lambda url: "zach-morris/repository.zachmorris",
        asset_filter=lambda name: name.lower().startswith('repository.zachmorris') and name.lower().endswith('.zip'),
        addon_name='Zach Morris Repo'
    )
