class ElnAppRouter:
    """Router for the ELN application."""

    @staticmethod
    def get_material_list_url() -> str:
        """Get the URL for the material list page.

        :return: The material list URL
        :rtype: str
        """
        return "/"

    @staticmethod
    def get_material_detail_url(material_id: str) -> str:
        """Get the URL for the material detail page.

        :param material_id: The ID of the material
        :type material_id: str
        :return: The material detail URL
        :rtype: str
        """
        return f"/materials/{material_id}"

    @staticmethod
    def get_batch_detail_url(batch_id: str) -> str:
        """Get the URL for the batch detail page.

        :param batch_id: The ID of the batch
        :type batch_id: str
        :return: The batch detail URL
        :rtype: str
        """
        return f"/batches/{batch_id}"

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
