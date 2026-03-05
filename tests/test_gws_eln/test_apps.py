from gws_eln.eln_app.generate_eln_app import GenerateElnApp
from gws_core.test.app_tester import AppTester
from gws_core.test.base_test_case import BaseTestCase


# test_apps
class TestApps(BaseTestCase):

    def test_eln_app(self):
        AppTester.test_app_from_task(
            test_case=self,
            generate_task_type=GenerateElnApp,
            app_output_name="reflex_app",
        )
