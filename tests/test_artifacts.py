import re
import unittest
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ArtifactTests(unittest.TestCase):
    def test_zabbix_template(self):
        xml = ROOT / 'zabbix/Tuya_Smart_Plug_by_TinyTuya_Zabbix_8.2.xml'
        root = ET.parse(xml).getroot()
        self.assertEqual(root.findtext('version'), '8.2')
        items = root.findall('.//templates/template/items/item')
        keys = {item.findtext('key') for item in items}
        self.assertIn('tuya.poll.ok', keys)
        self.assertIn('tuya.status.raw', keys)
        self.assertEqual(len(items), 8)
        ids = [n.text for n in root.iter('uuid')]
        self.assertEqual(len(ids), len(set(ids)))
        for raw in ids:
            parsed = uuid.UUID(hex=raw)
            self.assertEqual(parsed.version, 4)

    def test_no_personal_device_in_published_files(self):
        excluded = {'.gitignore', '.dockerignore'}
        for path in ROOT.rglob('*'):
            if not path.is_file() or path.name in excluded or '__pycache__' in path.parts:
                continue
            if path.suffix not in {'.py', '.xml', '.yml', '.yaml', '.sh', '.md', '.txt', ''}:
                continue
            text = path.read_text(encoding='utf-8', errors='replace')
            self.assertNotRegex(text, r'\bbf[0-9a-z]{20}\b', str(path))
            self.assertNotRegex(text, r'\b192\.168\.1\.108\b', str(path))


if __name__ == '__main__':
    unittest.main()
