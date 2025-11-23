# -*- coding: utf-8 -*-
# resources/lib/zacmorris_repo_installer.py

from resources.lib.repo_installer import install_github_release

def download_zacmorris_repo():
    """
    Scarica e installa direttamente il repository Zach Morris / IAGL.
    Il repo usa GitHub raw e contiene lo ZIP già pronto.
    """
    return install_github_release(
        source_predicate=lambda s: (
            "zach" in s.get("name", "").lower()
            or "zac" in s.get("name", "").lower()
            or "morris" in s.get("name", "").lower()
            or "iagl" in s.get("name", "").lower()
            or "repository.zachmorris" in s.get("name", "").lower()
        ),
        repo_path_extractor=lambda url: "zach-morris/repository.zachmorris",
        asset_filter=lambda name: name.lower().endswith(".zip"),
        addon_name="Zac Morris Repo"
    )
