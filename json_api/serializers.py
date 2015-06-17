
import six
from collections import OrderedDict
from django.core.exceptions import ImproperlyConfigured
from rest_framework.utils import model_meta
from rest_framework import serializers

from json_api import exceptions


class CheckedTypeField(serializers.Field):
    # The implementation here is a little weird.
    # - `source` needs to be set to '*', since there is no 'type' field on the
    #   model. 'type' is pulled from the model's meta. This is relevant to
    #   serialization of model instances.
    # - `source_attrs` needs to be abused and set to 'type' after binding,
    #   otherwise the serializer cannot save the type parameter. Even though
    #   there is no 'type' field, this okay as the idenity serializer should
    #   not be saved, only validated. ie, the serializer will never attempt
    #   to construct an actual instance of the model.
    def __init__(self, **kwargs):
        kwargs['source'] = '*'
        super(CheckedTypeField, self).__init__(**kwargs)

    def run_validation(self, data):
        expected = self.to_representation(data)
        if data != expected:
            raise exceptions.Conflict(
                'Incorrect type. Expected \'{}\', but got \'{}\'.'.format(
                    expected, data,
                )
            )
        return super(CheckedTypeField, self).run_validation(data)

    def bind(self, field_name, parent):
        ret = super(CheckedTypeField, self).bind(field_name, parent)
        self.source_attrs = ['type']
        return ret

    def to_internal_value(self, data):
        return six.text_type(data)

    def to_representation(self, value):
        return self.parent.Meta.model._meta.verbose_name


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
    A type of `ModelSerializer` that represents a resource identity. This
    serializer should be used for validating a resource identifier and getting
    its normalized ID.

    Reference:
    http://jsonapi.org/format/#document-structure-resource-identifier-objects
    """

    def get_default_field_names(self, declared_fields, model_info):
        return (model_info.pk.name, )

    def get_fields(self):
        # JSON-API normalizes on 'id' as the primary key field, so build
        # the pk field, and rename.
        fields = super(ResourceIdentifierSerializer, self).get_fields()
        return OrderedDict((
            ('id', fields[self._pk_field_name]),
            ('type', CheckedTypeField()),
        ))

    def save(self, *args, **kwargs):
        raise ImproperlyConfigured(
            "'%s' should not be used to create instances of a model."
            % self.__class__.__name__
        )

    def get_extra_kwargs(self):
        # We need to override extra_kwargs here, since the Meta class will
        # probably be overridden by the subclass.
        extra_kwargs = getattr(self.Meta, 'extra_kwargs', {})
        extra_kwargs.update({self._pk_field_name: {'read_only': False, }, })
        self.Meta.extra_kwargs = extra_kwargs
        return super(ResourceIdentifierSerializer, self).get_extra_kwargs()

    @property
    def _pk_field_name(self):
        meta = self.Meta.model._meta
        return model_meta._get_pk(meta).name


class PolymorphicResourceSerializer(ResourceSerializer):

    def __new__(cls, *args, **kwargs):
        instance = kwargs.get('instance', None)

        # get the serializer subclass for an instance, or default to base class
        serializer_class = cls
        if hasattr(instance, '_meta') and hasattr(cls.Meta, 'subclasses'):
            serializer_class = cls.Meta.subclasses.get(instance._meta.model, cls)

        return super(PolymorphicResourceSerializer, cls).__new__(serializer_class, *args, **kwargs)
