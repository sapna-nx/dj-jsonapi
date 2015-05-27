
from rest_framework import serializers


class ResourceSerializer(serializers.ModelSerializer):
    """
    A type of `ModelSerializer` that represents individual resources. It is
    agnostic to its identity and its relationships to other resources.
    """

    def get_default_field_names(self, declared_fields, model_info):
        """
        Return the default list of field names that will be used if the
        `Meta.fields` option is not specified.
        """
        return (
            list(declared_fields.keys()) +
            list(model_info.fields.keys())
        )
