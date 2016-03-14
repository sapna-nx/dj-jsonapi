
from collections import OrderedDict
from rest_framework.utils.model_meta import (
    get_field_info, FieldInfo, _merge_relationships
)

_drf_get_field_info = get_field_info


def get_field_info(model):
    """
    Given a model class, returns a `FieldInfo` instance, which is a
    `namedtuple`, containing metadata about the various field types on the model
    including information about their relationships.

    Note:
    This modifies DRF's implementation of `get_field_info` with the call to
    `_translate_reverse_relationships`, replacing accessor names with relation
    names.
    """
    field_info = _drf_get_field_info(model)._asdict()
    opts = model._meta.concrete_model._meta

    forward_relations = field_info['forward_relations']
    reverse_relations = field_info['reverse_relations']
    reverse_relations = _translate_reverse_relationships(opts, reverse_relations)
    relationships = _merge_relationships(forward_relations, reverse_relations)

    field_info.update({
        'reverse_relations': reverse_relations,
        'relations': relationships,
    })

    return FieldInfo(**field_info)


def _translate_reverse_relationships(opts, reverse_relations):
    """
    DRF's `_get_reverse_relationships` uses the `get_accessor_name` method of
    `ForeignObjectRel` as the key for the relationship. This function replaces
    those keys with the rel's `name` property. This allows us to later lookup
    the relationship with `opts.get_field()`.
    """
    return OrderedDict([(
        relation.name, reverse_relations.pop(relation.get_accessor_name())
    ) for relation in opts.related_objects])


def verbose_name(model):
    opts = model._meta

    if model._deferred:
        return verbose_name(opts.proxy_for_model)

    return opts.verbose_name
