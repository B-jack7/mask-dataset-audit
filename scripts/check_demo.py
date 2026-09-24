import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

root = Path(__file__).resolve().parents[1]
with TemporaryDirectory() as directory:
    data, report = Path(directory) / 'data', Path(directory) / 'report'
    subprocess.run([sys.executable, str(root / 'examples/make_demo.py'), str(data)], check=True)
    result = subprocess.run([sys.executable, '-m', 'mask_dataset_audit', str(data), '--labels', '0,1', '--out', str(report)])
    assert result.returncode == 1, result.returncode
    result = json.loads((report / 'report.json').read_text())
    assert result['summary']['errors'] == 4, result['summary']
print('Four planted errors found; CLI and report generation passed.')
