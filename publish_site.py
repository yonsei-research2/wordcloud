
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

FILES = {
    'index.html',
    'paper_explorer.html',
    '.nojekyll',
    'paper_explorer_assets/data.js',
    'paper_explorer_assets/images.js',
}
BRANCH = 'pages-data'


def git(store, *args, check=True):
    return subprocess.run(
        ['git', '-C', str(store), *args],
        check=check,
        text=True,
        capture_output=True,
    )


def copy_site(source, target):
    source = Path(source)
    files = [p for p in source.rglob('*') if p.is_file()]

    if not (source / 'index.html').is_file():
        raise ValueError('HTML 결과가 없습니다.')

    for file in files:
        name = file.relative_to(source).as_posix()
        if name not in FILES or file.is_symlink():
            raise ValueError(f'게시할 수 없는 파일: {name}')

    target.mkdir(parents=True, exist_ok=True)

    for file in files:
        dst = target / file.relative_to(source)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, dst)


def publish(store, site, result_id, bootstrap=None):
    store = Path(store).resolve()
    site = Path(site).resolve()
    is_example = result_id == 'example'

    if not is_example and not re.fullmatch('[a-f0-9]{32}', result_id):
        raise ValueError('잘못된 결과 ID입니다.')

    if store == site or store in site.parents:
        raise ValueError('새 결과는 보관 체크아웃 밖에 있어야 합니다.')

    git(store, 'config', 'user.name', 'github-actions[bot]')
    git(
        store,
        'config',
        'user.email',
        '41898282+github-actions[bot]@users.noreply.github.com',
    )

    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp) / 'site'

        # 새 결과를 먼저 검사합니다.
        copy_site(site, staged)

        for attempt in range(10):
            remote = git(
                store, 'ls-remote', '--heads', 'origin', BRANCH
            ).stdout.strip()
            old = remote.split()[0] if remote else None

            if old:
                git(store, 'fetch', '--depth=1', 'origin', BRANCH)
                git(store, 'checkout', '-B', BRANCH, 'FETCH_HEAD')
                git(store, 'reset', '--hard', 'FETCH_HEAD')
            else:
                git(store, 'switch', '--orphan', BRANCH)

                if bootstrap:
                    copy_site(Path(bootstrap), store)
                else:
                    (store / 'index.html').write_text(
                        '<!doctype html><meta charset="utf-8">'
                        '<title>논문 분석</title>'
                        '<p>전달받은 개별 결과 링크로 접속하세요.</p>',
                        encoding='utf-8',
                    )

            if is_example:
                target = store / 'example'
            else:
                target = store / 'results' / result_id

            if target.exists() or target.is_symlink():
                if not is_example:
                    raise ValueError(
                        '이미 사용한 결과 ID입니다. '
                        '기존 결과를 덮어쓰지 않습니다.'
                    )

                if target.is_symlink() or not target.is_dir():
                    raise ValueError('example은 일반 폴더여야 합니다.')

                # 고정 예제 폴더만 교체합니다.
                shutil.rmtree(target)

            copy_site(staged, target)
            (store / '.nojekyll').touch()
            git(store, 'add', '.')

            diff = git(
                store, 'diff', '--cached', '--quiet', check=False
            )

            if diff.returncode == 0:
                return

            if diff.returncode != 1:
                diff.check_returncode()

            message = (
                'Update example'
                if is_example
                else f'Add result {result_id}'
            )
            git(store, 'commit', '-m', message)

            pushed = git(
                store,
                'push',
                'origin',
                f'HEAD:refs/heads/{BRANCH}',
                check=False,
            )

            if pushed.returncode == 0:
                return

            current = git(
                store, 'ls-remote', '--heads', 'origin', BRANCH
            ).stdout.strip()

            current_sha = current.split()[0] if current else None

            if current_sha == old:
                raise RuntimeError(
                    '결과 보관 브랜치 업로드 실패: ' + pushed.stderr
                )

        raise RuntimeError(
            '동시 게시 충돌이 계속되었습니다. 실행을 다시 시도하세요.'
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--result-id', required=True)
    parser.add_argument('--bootstrap', type=Path)
    args = parser.parse_args()

    publish(
        args.store,
        args.site,
        args.result_id,
        args.bootstrap,
    )
