from gws_core import ApiRegistry, Settings


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

    @classmethod
    def get_eln_api_url(cls) -> str:
        """Get the full API URL for the ELN brick.

        :return: The ELN API URL
        """
        base_url = Settings.get_lab_api_url().rstrip("/")
        route_path = cls.get_eln_api_route_path().lstrip("/")
        return f"{base_url}/{route_path}"


# Register the app so it gets mounted at /brick/gws_eln/
# The registry creates the FastAPI instance and adds standard exception handlers.
eln_api = ApiRegistry.register_brick_api(ELNSettings.get_brick_name())
