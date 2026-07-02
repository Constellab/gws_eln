import reflex as rx
from gws_core.core.exception.exceptions.base_http_exception import BaseHTTPException
from gws_core.core.utils.logger import Logger
from gws_reflex_base import ReflexAppException
from gws_reflex_main import ReflexMainState

_TOAST_POSITION = "top-right"


def eln_backend_exception_handler(exception: Exception) -> rx.event.EventSpec | None:
    """Backend exception handler for the ELN app.

    Same behavior as the gws default handler, but toasts are shown top-right
    instead of top-center, so every error toast in the app is consistent.
    """
    if isinstance(exception, ReflexAppException):
        if exception.show_as == "info":
            return rx.toast.info(exception.detail, position=_TOAST_POSITION)
        return rx.toast.error(exception.detail, position=_TOAST_POSITION)

    if isinstance(exception, BaseHTTPException):
        if exception.show_as == "info":
            return rx.toast.info(exception.get_detail_with_args(), position=_TOAST_POSITION)
        return rx.toast.error(exception.get_detail_with_args(), position=_TOAST_POSITION)

    Logger.log_exception_stack_trace(exception)

    if ReflexMainState.is_dev_mode():
        return rx.toast.error(
            f"An unexpected error occurred: {str(exception)}", position=_TOAST_POSITION
        )
    return rx.toast.error("An unexpected error occurred.", position=_TOAST_POSITION)
