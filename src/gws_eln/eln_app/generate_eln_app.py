from gws_core import (
    AppConfig,
    AppType,
    ConfigParams,
    ConfigSpecs,
    InputSpecs,
    OutputSpec,
    OutputSpecs,
    ReflexResource,
    Task,
    TaskInputs,
    TaskOutputs,
    app_decorator,
    task_decorator,
)


@app_decorator("ElnAppAppConfig", app_type=AppType.REFLEX, human_name="Generate ElnApp app")
class ElnAppAppConfig(AppConfig):
    # retrieve the path of the app folder, relative to this file
    # the app code folder starts with a underscore to avoid being loaded when the brick is loaded
    def get_app_folder_path(self):
        return self.get_app_folder_from_relative_path(__file__, "_eln_app")


@task_decorator("GenerateElnApp", human_name="Generate ELN app", style=ReflexResource.copy_style())
class GenerateElnApp(Task):
    """
    Task that generates the ElnApp app.
    """

    input_specs = InputSpecs()
    output_specs = OutputSpecs({"reflex_app": OutputSpec(ReflexResource)})

    config_specs = ConfigSpecs({})

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:
        """Run the task"""

        reflex_app = ReflexResource()

        reflex_app.set_app_config(ElnAppAppConfig())
        reflex_app.name = "Eln App"
        reflex_app.set_requires_authentication(False)

        return {"reflex_app": reflex_app}
