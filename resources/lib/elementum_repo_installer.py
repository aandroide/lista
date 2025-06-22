# resources/lib/elementum_repo_installer.py
import re
from resources.lib.repo_installer import install_github_release

def download_elementum_repo():
    return install_github_release(
        source_predicate=lambda s: s.get('name', '').lower() == 'elementum repo',
        repo_path_extractor=lambda url: re.search(r'https://github.com/([^/]+/[^/]+)', url).group(1),
        asset_filter=lambda name: 'repository.elementumorg' in name.lower() and name.lower().endswith('.zip'),
        addon_name='Elementum Repo'
    )
