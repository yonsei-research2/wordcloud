"""Noninteractive entry point for the original Colab v8.4 pipeline."""
import argparse
import json
from pathlib import Path
import zipfile

import author_keyword_pipeline_v8 as pipeline


def apply_config(path):
    settings = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(settings, dict):
        raise ValueError('설정 파일은 JSON 객체여야 합니다.')
    for name, value in settings.items():
        if not name.isupper() or not hasattr(pipeline, name):
            raise ValueError(f'알 수 없는 설정: {name}')
        default = getattr(pipeline, name)
        if isinstance(default, set):
            if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
                raise ValueError(f'{name}: 문자열 배열이 필요합니다.')
            value = set(value)
        elif name == 'SHEET_NAME':
            if not isinstance(value, (int, str)) or isinstance(value, bool):
                raise ValueError('SHEET_NAME: 시트 번호 또는 이름이 필요합니다.')
        elif default is not None:
            if isinstance(default, bool):
                valid = isinstance(value, bool)
            elif isinstance(default, (int, float)):
                valid = isinstance(value, (int, float)) and not isinstance(value, bool)
            else:
                valid = isinstance(value, type(default))
            if not valid:
                raise ValueError(f'{name}: 설정 값 형식이 올바르지 않습니다.')
        setattr(pipeline, name, value)


def package_results(out, archive):
    required = ['analysis.xlsx', 'paper_explorer.html',
                'paper_explorer_assets/data.js', 'paper_explorer_assets/images.js']
    required += [f'wordcloud_{v}.png' for v in pipeline.SCORE_FIELDS]
    for name in required:
        if not (out / name).is_file():
            raise RuntimeError(f'필수 결과물이 없습니다: {name}')
    # The pipeline can record NLP failures without raising. CI must flag those.
    from openpyxl import load_workbook
    wb = load_workbook(out / 'analysis.xlsx', read_only=True, data_only=True)
    try:
        errors = list(wb['오류'].iter_rows(min_row=2, values_only=True))
        if any(any(v is not None for v in row) for row in errors):
            raise RuntimeError('형태소 분석 오류가 있습니다. analysis.xlsx의 오류 시트를 확인하세요.')
    finally:
        wb.close()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in required:
            z.write(out / name, name)


def main():
    parser = argparse.ArgumentParser(description='Excel 논문 키워드 분석 → Excel, PNG, HTML, ZIP')
    parser.add_argument('input', type=Path)
    parser.add_argument('--mode', choices=['sample', 'full'], default='sample')
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('config.json'))
    parser.add_argument('--output-dir', type=Path, default=Path('output'))
    parser.add_argument('--font-path', type=Path, help='시스템 폰트 대신 사용할 TTF 경로')
    parser.add_argument('--cache-dir', type=Path, default=Path('nlp_cache'))
    args = parser.parse_args()
    if not args.input.is_file() or args.input.suffix.lower() != '.xlsx':
        parser.error('입력 파일은 존재하는 .xlsx 파일이어야 합니다.')
    # Prevent stale outputs from being mistaken for a successful new run.
    target = args.output_dir / args.mode
    if target.exists() and any(target.iterdir()):
        parser.error(f'출력 폴더가 비어 있지 않습니다: {target}. 새 경로를 지정하세요.')
    apply_config(args.config)
    if args.font_path:
        pipeline.WORDCLOUD_FONT_PATH = str(args.font_path.resolve())
    out = pipeline.run(str(args.input), args.mode, args.output_dir, args.cache_dir)
    archive = args.output_dir / f'v8_4_{args.mode}_results.zip'
    package_results(out, archive)
    print(f'완료: {archive.resolve()}')


if __name__ == '__main__':
    main()
