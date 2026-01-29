import reflex as rx
from gws_reflex_main import form_dialog_component

from .location_form_dialog_state import LocationFormDialogState


def _form_content() -> rx.Component:
    """Form content for entering location details."""
    return rx.vstack(
        # Location Name field
        rx.vstack(
            rx.text("Location Name*", size="2", weight="bold"),
            rx.input(
                placeholder="Enter location name",
                name="name",
                required=True,
                width="100%",
                default_value=LocationFormDialogState.form_name,
            ),
            width="100%",
            spacing="1",
        ),
        # Description field
        rx.vstack(
            rx.text("Description", size="2", weight="bold"),
            rx.text_area(
                placeholder="Enter location description (optional)",
                name="description",
                width="100%",
                default_value=LocationFormDialogState.form_description,
                rows="3",
            ),
            width="100%",
            spacing="1",
        ),
        width="100%",
        spacing="3",
    )


def _dialog() -> rx.Component:
    """The base dialog component without a trigger.

    This can be reused in different contexts with different triggers.

    :return: The dialog component
    :rtype: rx.Component
    """
    return form_dialog_component(
        state=LocationFormDialogState,
        title=rx.cond(LocationFormDialogState.is_update_mode, "Update Location", "Create New Location"),
        description=rx.cond(
            LocationFormDialogState.is_update_mode,
            "Update the location details below.",
            "Fill in the details below to create a new location.",
        ),
        form_content=_form_content(),
        max_width="450px",
    )


def create_location_dialog() -> rx.Component:
    """Dialog component for creating a new location with a trigger button.

    Displays a form for entering location details. Success and error messages
    are displayed as toast notifications.

    :return: The create location dialog component with trigger button
    :rtype: rx.Component
    """
    return rx.fragment(
        rx.button(
            rx.icon("plus", size=18), "Create New Location", size="3", on_click=LocationFormDialogState.open_create_dialog
        ),
        _dialog(),
    )


def location_update_dialog() -> rx.Component:
    """Dialog component for updating an existing location.

    This component provides just the dialog (without a trigger button).
    The dialog is controlled by the LocationFormDialogState.dialog_opened state.

    :return: The update location dialog component
    :rtype: rx.Component
    """
    return _dialog()
