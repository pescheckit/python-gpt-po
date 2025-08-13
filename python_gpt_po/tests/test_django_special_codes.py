"""
Test Django special language code handling.
"""
import unittest

from python_gpt_po.services.po_file_handler import POFileHandler


class TestDjangoSpecialCodes(unittest.TestCase):
    """Test that Django special language codes are handled correctly."""

    def test_is_django_special_code(self):
        """Test detection of Django special language codes."""
        handler = POFileHandler()

        # Chinese variants should be recognized
        self.assertTrue(handler._is_django_special_code('zh_Hans'))
        self.assertTrue(handler._is_django_special_code('zh_Hant'))
        self.assertTrue(handler._is_django_special_code('zh-hans'))
        self.assertTrue(handler._is_django_special_code('zh-hant'))
        self.assertTrue(handler._is_django_special_code('zh_CN'))
        self.assertTrue(handler._is_django_special_code('zh_TW'))
        self.assertTrue(handler._is_django_special_code('zh_HK'))

        # Serbian variants should be recognized
        self.assertTrue(handler._is_django_special_code('sr_Latn'))
        self.assertTrue(handler._is_django_special_code('sr-latn'))
        self.assertTrue(handler._is_django_special_code('sr@latin'))

        # Norwegian variants should be recognized
        self.assertTrue(handler._is_django_special_code('no'))
        self.assertTrue(handler._is_django_special_code('nb'))
        self.assertTrue(handler._is_django_special_code('nn'))

        # Belarusian variant should be recognized
        self.assertTrue(handler._is_django_special_code('be@tarask'))

        # Regional English variants should be recognized
        self.assertTrue(handler._is_django_special_code('en_AU'))
        self.assertTrue(handler._is_django_special_code('en_GB'))

        # Regional Spanish variants should be recognized
        self.assertTrue(handler._is_django_special_code('es_AR'))
        self.assertTrue(handler._is_django_special_code('es_MX'))
        self.assertTrue(handler._is_django_special_code('es_CO'))

        # Portuguese variant should be recognized
        self.assertTrue(handler._is_django_special_code('pt_BR'))

        # Regular codes should not be recognized as special
        self.assertFalse(handler._is_django_special_code('fr'))
        self.assertFalse(handler._is_django_special_code('de'))
        self.assertFalse(handler._is_django_special_code('es'))
        self.assertFalse(handler._is_django_special_code('en'))

    def test_normalize_language_code_with_special_codes(self):
        """Test normalization of Django special language codes."""
        handler = POFileHandler()

        # Chinese variants should normalize to 'zh'
        self.assertEqual(handler.normalize_language_code('zh_Hans'), 'zh')
        self.assertEqual(handler.normalize_language_code('zh_Hant'), 'zh')
        self.assertEqual(handler.normalize_language_code('zh-hans'), 'zh')
        self.assertEqual(handler.normalize_language_code('zh-hant'), 'zh')
        self.assertEqual(handler.normalize_language_code('zh_CN'), 'zh')
        self.assertEqual(handler.normalize_language_code('zh_TW'), 'zh')

        # Serbian variants should normalize to 'sr'
        self.assertEqual(handler.normalize_language_code('sr_Latn'), 'sr')
        self.assertEqual(handler.normalize_language_code('sr-latn'), 'sr')
        self.assertEqual(handler.normalize_language_code('sr@latin'), 'sr')

        # Norwegian should stay as-is
        self.assertEqual(handler.normalize_language_code('no'), 'no')
        self.assertEqual(handler.normalize_language_code('nb'), 'nb')
        self.assertEqual(handler.normalize_language_code('nn'), 'nn')

        # Belarusian variant should normalize to 'be'
        self.assertEqual(handler.normalize_language_code('be@tarask'), 'be')

        # Regional variants should normalize to base language
        self.assertEqual(handler.normalize_language_code('en_AU'), 'en')
        self.assertEqual(handler.normalize_language_code('en_GB'), 'en')
        self.assertEqual(handler.normalize_language_code('es_AR'), 'es')
        self.assertEqual(handler.normalize_language_code('pt_BR'), 'pt')

        # Regular codes should work as before
        self.assertEqual(handler.normalize_language_code('fr'), 'fr')
        self.assertEqual(handler.normalize_language_code('fr_CA'), 'fr')
        self.assertEqual(handler.normalize_language_code('fr-CA'), 'fr')


if __name__ == '__main__':
    unittest.main()
