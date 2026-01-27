from gws_core import ApiRegistry


class ELNSettings:
    """Settings for the ELN brick."""

    @classmethod
    def get_brick_name(cls) -> str:
        """Get the brick name for the ELN brick.

        :return: The ELN brick name
        """
        return "gws_eln"

    @classmethod
    def get_eln_api_route_path(cls) -> str:
        """Get the API route path for the ELN brick.

        :return: The ELN API route path
        """
        return ApiRegistry.get_brick_api_path(cls.get_brick_name())


# Register the app so it gets mounted at /brick/gws_eln/
# The registry creates the FastAPI instance and adds standard exception handlers.
eln_api = ApiRegistry.register_brick_api(ELNSettings.get_brick_name())
