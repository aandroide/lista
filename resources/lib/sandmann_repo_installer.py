# -*- coding: utf-8 -*-
# resources/lib/sandmann_repo_installer.py
from resources.lib.repo_installer import install_github_release

def download_sandmann_repo():
    return install_github_release(
        source_predicate=lambda s: 'sandmann79' in s.get('name', '').lower() and 'amazon' in s.get('name', '').lower(),
        repo_path_extractor=lambda url: url,  # URL già API JSON
        asset_filter=lambda name: name.lower().endswith('.zip'),
        addon_name='Sandmann Repo'
    )
