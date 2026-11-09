#!/usr/bin/env python3
"""Create a deterministic Lambda layer ZIP from an installed dependency directory."""
import argparse
import zipfile
from pathlib import Path


def package(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source.rglob('*')):
            if not path.is_file():
                continue
            relative = path.relative_to(source)
            if '__pycache__' in relative.parts or relative.parts[0] == 'bin' or path.suffix in ('.pyc', '.pyo'):
                continue
            # Project helpers are archived separately by Terraform.
            if relative.as_posix() in ('starchild_stripe.py', 'order_validation.py'):
                continue
            info = zipfile.ZipInfo(f'python/{relative.as_posix()}', date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o100644 << 16)
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    package(args.source, args.output)
