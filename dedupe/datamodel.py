import pkgutil

from collections import OrderedDict
from itertools import combinations_with_replacement

import dedupe.variables
import dedupe.variables.base as base
from dedupe.variables.base import MissingDataType
from dedupe.variables.interaction import InteractionType
from dedupe.variables.base import DerivedType

for _, module, _  in pkgutil.iter_modules(dedupe.variables.__path__, 
                                          'dedupe.variables.') :
    __import__(module)


FIELD_CLASSES = dict(base.allSubclasses(base.FieldType))

class DataModel(dict) :

    def __init__(self, fields):

        self['bias'] = 0

        primary_fields, data_model = typifyFields(fields)
        self.derived_start = len(data_model)
        self.primary_fields = primary_fields

        data_model += interactions(fields, primary_fields)
        data_model += missing(data_model)

        self.polynomial_expansion = []
        # for combo in combinations_with_replacement(enumerate(data_model), 2) :
        #     (i_1, var_1), (i_2, var_2) = combo
        #     definition = {'name' : str((var_1.name, var_2.name)),
        #                   'type' : 'polynomial expansion'}
        #     data_model.append(DerivedType(definition))
        #     self.polynomial_expansion.append((i_1, i_2))

        self['fields'] = data_model
        self.n_fields = len(self['fields'])


    # Changing this from a property to just a normal attribute causes
    # pickling problems, because we are removing static methods from
    # their class context. This could be fixed by defining comparators
    # outside of classes in fieldclasses
    @property 
    def field_comparators(self) :
        start = 0
        stop = 0
        comparators = []
        for field in self.primary_fields :
            stop = start + len(field) 
            comparators.append((field.field, field.comparator, start, stop))
            start = stop

        return comparators

    @property 
    def missing_field_indices(self) : 
        return [i for i, definition 
                in enumerate(self['fields'])
                if definition.has_missing]

    @property
    def interactions(self) :
        indices = []

        fields = self['fields']
        field_names = [field.name for field in fields]

        for definition in fields :
            if hasattr(definition, 'interaction_fields') :
                interaction_indices = []
                for interaction_field in definition.interaction_fields :
                    interaction_indices.append(field_names.index(interaction_field))
                indices.append(interaction_indices)
                
        return indices

def typifyFields(fields) :
    primary_fields = []
    data_model = []

    for definition in fields :
        try :
            field_type = definition['type']
        except TypeError :
            raise TypeError("Incorrect field specification: field "
                            "specifications are dictionaries that must "
                            "include a type definition, ex. "
                            "{'field' : 'Phone', type: 'String'}")
        except KeyError :
            raise KeyError("Missing field type: fields "
                           "specifications are dictionaries that must "
                           "include a type definition, ex. "
                           "{'field' : 'Phone', type: 'String'}")
            
        if field_type == 'Interaction' :
            continue

        try :
            field_class = FIELD_CLASSES[field_type]
        except KeyError :
            raise KeyError("Field type %s not valid. Valid types include %s"
                           % (definition['type'], ', '.join(FIELD_CLASSES)))

        field_object = field_class(definition)
        primary_fields.append(field_object)
        
        if hasattr(field_object, 'higher_vars') :
            data_model.extend(field_object.higher_vars)
        else :
            data_model.append(field_object)

    return primary_fields, data_model

def missing(data_model) :
    missing_variables = []
    for definition in data_model[:] :
        if definition.has_missing :
            missing_variables.append(MissingDataType(definition.name))

    return missing_variables

def interactions(definitions, primary_fields) :
    field_d = {field.name : field for field in primary_fields}
    interaction_class = InteractionType

    interactions = []

    for definition in definitions :
        if definition['type'] == 'Interaction' :
            field = interaction_class(definition)
            field.expandInteractions(field_d)
            interactions.extend(field.higher_vars)

    return interactions



