from django.test import TestCase, override_settings
from singletons.config_manager import ConfigManager

# Create your tests here.
class ConfigTest(TestCase):
    def test_singleton_behavior(self):
    
#     def tearDown(self):
#         if hasattr(config_manager, '_reset'):
#             config_manager._reset()
            
#     @override_settings(MY_APP_CONFIG='test_key')
#     def test_custom_config(self):
        
#         self.assertEqual(get_config(), 'test_key')
        
#     @override_settings(MY_APP_CONFIG='new_test')
#     def test_config_change(self):
        
#         self.assertEqual(get_config(), 'new_test')
        
        config1 = ConfigManager()
        config2 = ConfigManager()

        assert config1 is config2
        config1.set_setting("DEFAULT_PAGE_SIZE", 50)
        assert config2.get_setting("DEFAULT_PAGE_SIZE") == 50