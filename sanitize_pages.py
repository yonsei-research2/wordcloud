"""Rebuild an existing Pages artifact without its Excel/ZIP downloads."""
import argparse
from pathlib import Path
import tarfile
import tempfile

from build_pages import build_site


def sanitize_pages(artifact, site_dir):
    needed = {'paper_explorer.html', 'paper_explorer_assets/data.js',
              'paper_explorer_assets/images.js'}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        out = root / 'sample'
        with tarfile.open(artifact) as archive:
            found = set()
            for member in archive.getmembers():
                name = member.name.removeprefix('./')
                if name not in needed:
                    continue
                if name in found or not member.isfile():
                    raise ValueError(f'정상 HTML 자산이 아닙니다: {name}')
                target = out / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source:
                    target.write_bytes(source.read())
                found.add(name)
            if found != needed:
                raise ValueError('기존 Pages 아티팩트에 필요한 HTML 자산이 없습니다.')
        return build_site(root, 'sample', site_dir)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifact', type=Path)
    parser.add_argument('--site-dir', type=Path, default=Path('site'))
    args = parser.parse_args()
    sanitize_pages(args.artifact, args.site_dir)
