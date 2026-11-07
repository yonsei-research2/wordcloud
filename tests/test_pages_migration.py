import io
from pathlib import Path
import tarfile
import tempfile
import unittest

from sanitize_pages import sanitize_pages


class MigrationTest(unittest.TestCase):
    def test_preserves_published_assets_without_private_files(self):
        original = b'<html><main>Existing research</main></html>'
        files = {'paper_explorer.html': original,
                 'index.html': b'<nav>old downloads</nav>' + original,
                 'paper_explorer_assets/data.js': b'published data',
                 'paper_explorer_assets/images.js': b'published images',
                 'results.zip': b'private zip', 'analysis.xlsx': b'private excel',
                 '../escape.txt': b'must not extract'}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / 'artifact.tar'
            with tarfile.open(artifact, 'w') as archive:
                for name, data in files.items():
                    member = tarfile.TarInfo('./' + name)
                    member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))
            site = sanitize_pages(artifact, root / 'site')
            self.assertEqual((site / 'index.html').read_bytes(), original)
            self.assertEqual((site / 'paper_explorer_assets/data.js').read_bytes(),
                             b'published data')
            self.assertFalse((site / 'results.zip').exists())
            self.assertFalse((site / 'analysis.xlsx').exists())
            self.assertFalse((root / 'escape.txt').exists())
