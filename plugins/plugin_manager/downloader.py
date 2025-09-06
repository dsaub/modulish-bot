"""Utility functions to download a GitHub repository as a plugin without requiring git.

Supports specs like:
  owner/repo
  owner/repo@branch

Workflow:
 1. Build archive URL (tries branch then master if not specified explicitly).
 2. Download zip to temp file.
 3. Extract zip.
 4. Move extracted root folder into plugins/<repo_name> (fail if exists).
 5. Return target directory path.

Limitations:
 - Assumes plugin content (plugin.toml) is at repo root.
 - No checksum verification.
 - Minimal error handling for network issues.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import urllib.request
import zipfile
from typing import Optional, Tuple


class DownloadError(Exception):
    pass


def parse_spec(spec: str) -> Tuple[str, str, Optional[str]]:
    if '@' in spec:
        repo_part, branch = spec.split('@', 1)
    else:
        repo_part, branch = spec, None
    if '/' not in repo_part:
        raise DownloadError("El formato debe ser owner/repo o owner/repo@branch")
    owner, repo = repo_part.split('/', 1)
    return owner, repo, branch


def build_candidate_urls(owner: str, repo: str, branch: Optional[str]):
    candidates = []
    if branch:
        candidates.append(f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}")
    else:
        # Try main then master
        candidates.append(f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/main")
        candidates.append(f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/master")
    return candidates


def download_zip(url: str, dest_path: str):
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:  # nosec B310 (simple fetch)
            if resp.status != 200:
                raise DownloadError(f"HTTP {resp.status}")
            with open(dest_path, 'wb') as f:
                shutil.copyfileobj(resp, f)
    except Exception as e:
        raise DownloadError(f"Fallo descargando {url}: {e}") from e


def extract_zip(zip_path: str, target_dir: str) -> str:
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            root_names = {n.split('/')[0] for n in zf.namelist() if '/' in n}
            zf.extractall(target_dir)
        if not root_names:
            raise DownloadError("Archivo zip vacío o inesperado")
        # Usually only one root folder
        root_folder = sorted(root_names)[0]
        return os.path.join(target_dir, root_folder)
    except zipfile.BadZipFile as e:
        raise DownloadError(f"Zip corrupto: {e}") from e


def install_repo_as_plugin(spec: str, plugins_dir: str = 'plugins') -> str:
    owner, repo, branch = parse_spec(spec.strip())
    target_plugin_dir = os.path.join(plugins_dir, repo)
    if os.path.exists(target_plugin_dir):
        raise DownloadError(f"El plugin '{repo}' ya existe.")

    candidates = build_candidate_urls(owner, repo, branch)
    tmp_dir = tempfile.mkdtemp(prefix="plugin_dl_")
    zip_path = os.path.join(tmp_dir, 'repo.zip')
    extracted_root = None
    last_error = None
    try:
        for url in candidates:
            try:
                download_zip(url, zip_path)
                extracted_root = extract_zip(zip_path, tmp_dir)
                break
            except Exception as e:  # capture and try next candidate
                last_error = e
                continue
        if not extracted_root:
            raise DownloadError(f"No se pudo descargar el repo. Último error: {last_error}")

        # Expect plugin.toml at root
        plugin_toml = os.path.join(extracted_root, 'plugin.toml')
        if not os.path.isfile(plugin_toml):
            raise DownloadError("El repositorio no contiene plugin.toml en el root")

        shutil.move(extracted_root, target_plugin_dir)
        return target_plugin_dir
    finally:
        # Leave plugin dir; remove temp leftovers if still present
        try:
            if os.path.isdir(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
