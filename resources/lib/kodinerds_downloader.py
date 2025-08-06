# -*- coding: utf-8 -*-
# resources/lib/kodinerds_downloader.py
from resources.lib.repo_installer import install_from_html

def download_latest_kodinerds_zip():
    return install_from_html(
        source_predicate=lambda s: s.get('name', '').lower() == 'kodinerds repo',
        zip_pattern=r'repository\.kodinerds.*\.zip$',
        addon_name='Kodinerds'
    )
