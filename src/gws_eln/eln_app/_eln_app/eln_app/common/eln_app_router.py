class ElnAppRouter:
    """Router for the ELN application."""

    @staticmethod
    def get_home_url() -> str:
        """Get the URL for the home page (the two entry-point cards).

        :return: The home URL
        :rtype: str
        """
        return "/"

    @staticmethod
    def get_notes_list_url() -> str:
        """Get the URL for the notes list page.

        :return: The notes list URL
        :rtype: str
        """
        return "/notes"

    @staticmethod
    def get_note_detail_url(note_id: str) -> str:
        """Get the URL for the note detail page.

        :param note_id: The ID of the note
        :type note_id: str
        :return: The note detail URL
        :rtype: str
        """
        return f"/notes/{note_id}"

    @staticmethod
    def get_item_sheet_list_url() -> str:
        """Get the URL for the item_sheet list page.

        :return: The item_sheet list URL
        :rtype: str
        """
        return "/item_sheets"

    @staticmethod
    def get_item_sheet_detail_url(item_sheet_id: str) -> str:
        """Get the URL for the item_sheet detail page.

        :param item_sheet_id: The ID of the item_sheet
        :type item_sheet_id: str
        :return: The item_sheet detail URL
        :rtype: str
        """
        return f"/item_sheets/{item_sheet_id}"

    @staticmethod
    def get_item_detail_url(item_id: str) -> str:
        """Get the URL for the item detail page.

        :param item_id: The ID of the item
        :type item_id: str
        :return: The item detail URL
        :rtype: str
        """
        return f"/items/{item_id}"

    @staticmethod
    def get_location_list_url() -> str:
        """Get the URL for the location list page.

        :return: The location list URL
        :rtype: str
        """
        return "/locations"

    @staticmethod
    def get_supplier_list_url() -> str:
        """Get the URL for the supplier list page.

        :return: The supplier list URL
        :rtype: str
        """
        return "/suppliers"
