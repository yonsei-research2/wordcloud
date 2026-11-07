from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import publish_site as publisher


def git(path, *args):
    return subprocess.run(['git', '-C', str(path), *args], check=True,
                          capture_output=True, text=True).stdout


class MultiSiteTest(unittest.TestCase):
    def test_multiple_results_and_concurrent_publish_preserve_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = root / 'remote.git'
            subprocess.run(['git', 'init', '--bare', str(remote)], check=True, capture_output=True)
            seed = root / 'seed'
            subprocess.run(['git', 'clone', str(remote), str(seed)], check=True, capture_output=True)
            git(seed, 'checkout', '-b', 'main')
            git(seed, 'config', 'user.name', 'Test')
            git(seed, 'config', 'user.email', 'test@example.com')
            (seed / 'source.py').write_text('original analysis code')
            git(seed, 'add', '.')
            git(seed, 'commit', '-m', 'Source')
            git(seed, 'push', 'origin', 'main')
            stores = []
            for i in range(3):
                store = root / f'store{i}'
                subprocess.run(['git', 'clone', '--branch', 'main', str(remote), str(store)],
                               check=True, capture_output=True)
                stores.append(store)
            def site(name):
                path = root / name
                (path / 'paper_explorer_assets').mkdir(parents=True)
                (path / 'index.html').write_text(name)
                (path / 'paper_explorer_assets/data.js').write_text(name + ' data')
                return path
            original, a, b, c = [site(n) for n in ['original', 'a', 'b', 'c']]
            ids = ['a' * 32, 'b' * 32, 'c' * 32]
            publisher.publish(stores[0], a, ids[0], original)
            real_git = publisher.git
            raced = False
            def racing_git(store, *args, **kwargs):
                nonlocal raced
                if Path(store) == stores[1] and args[0] == 'push' and not raced:
                    raced = True
                    publisher.publish(stores[2], c, ids[2])
                return real_git(store, *args, **kwargs)
            with patch('publish_site.git', side_effect=racing_git):
                publisher.publish(stores[1], b, ids[1])
            self.assertTrue(raced)
            for id_, name in zip(ids, ['a', 'b', 'c']):
                self.assertEqual(git(stores[1], 'show', f'HEAD:results/{id_}/index.html').strip(), name)
                self.assertEqual(git(stores[1], 'show', f'HEAD:results/{id_}/paper_explorer_assets/data.js').strip(), name + ' data')
            self.assertEqual(git(stores[1], 'show', 'HEAD:index.html').strip(), 'original')
            self.assertNotIn('source.py', git(stores[1], 'ls-tree', '-r', '--name-only', 'HEAD'))
            with self.assertRaises(ValueError):
                publisher.publish(stores[1], b, ids[0])
            with self.assertRaises(ValueError):
                publisher.publish(stores[1], b, '../escape')
