
import six
from rest_framework import serializers

from json_api import exceptions


class CheckedTypeField(serializers.Field):

    def run_validation(self, data):
        expected = self.to_representation()
        if data != expected:
            raise exceptions.Conflict(
                'Incorrect type. Expected {expected_type}, but got {input_type}'.format(
                    expected, data,
                )
            )
        return super(CheckedTypeField, self).run_validation(data)

    def to_internal_value(self, data):
        return six.text_type(data)

    def to_representation(self, value=None):
        # ignore the incoming value
        return self.Meta.model._meta.verbose_name


class ResourceSerializer(serializers.ModelSerializer):
    """
    A type of `ModelSerializer` that represents a resource object's attributes.
    It is agnostic to its identity and its relationships to other resources.

    Reference:
    http://jsonapi.org/format/#document-structure-resource-objects
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


class ResourceIdentifierSerializer(serializers.ModelSerializer):
    """
    A type of `ModelSerializer` that represents a resource identity.

    Reference:
    http://jsonapi.org/format/#document-structure-resource-identifier-objects
    """
    type = CheckedTypeField()

    def get_default_field_names(self, declared_fields, model_info):
        """
        Return the default list of field names that will be used if the
        `Meta.fields` option is not specified.
        """
        return (
            [model_info.pk.name] +
            list(declared_fields.keys())
        )
