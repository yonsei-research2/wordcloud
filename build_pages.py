"""Publish only the HTML explorer and its browser assets to GitHub Pages."""
import argparse
from pathlib import Path
import shutil


def build_site(output_root, mode, site_dir):
    output_root, site_dir = Path(output_root), Path(site_dir)
    out = output_root / mode
    files = ['paper_explorer.html',
             'paper_explorer_assets/data.js', 'paper_explorer_assets/images.js']
    for path in [out / f for f in files]:
        if not path.is_file():
            raise FileNotFoundError(f'필수 분석 결과가 없습니다: {path}')
    source = (out / 'paper_explorer.html').read_text(encoding='utf-8')
    if source.count('<main>') != 1:
        raise ValueError('분석 HTML에서 본문을 찾을 수 없습니다.')
    if site_dir.exists() and any(site_dir.iterdir()):
        raise ValueError(f'게시 폴더가 비어 있지 않습니다: {site_dir}')
    site_dir.mkdir(parents=True, exist_ok=True)
    for name in files:
        target = site_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out / name, target)
    (site_dir / 'index.html').write_text(
        source, encoding='utf-8')
    (site_dir / '.nojekyll').touch()
    return site_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, default=Path('output'))
    parser.add_argument('--mode', choices=['sample', 'full'], required=True)
    parser.add_argument('--site-dir', type=Path, default=Path('site'))
    args = parser.parse_args()
    print(f'Pages 게시 파일 준비 완료: {build_site(args.output_root, args.mode, args.site_dir)}')


if __name__ == '__main__':
    main()
