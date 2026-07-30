function validate_descriptor_definition(definition, configDescriptorNames, errorId)
%VALIDATE_DESCRIPTOR_DEFINITION Validate descriptor schema and order.
    if ~isstruct(definition) || ~isscalar(definition)
        throw(MException(errorId, ...
            'Descriptor definition root must be a JSON object'));
    end
    if ~isfield(definition, 'schema_version')
        throw(MException(errorId, ...
            'Descriptor definition missing schema_version'));
    end
    schemaVersion = validate_text_scalar(definition.schema_version, ...
        'Descriptor definition schema_version', errorId);
    if ~strcmp(schemaVersion, '1.0')
        throw(MException(errorId, ...
            'Descriptor definition schema_version "%s" does not match frozen "1.0"', ...
            schemaVersion));
    end
    if ~isfield(definition, 'descriptors')
        throw(MException(errorId, ...
            'Descriptor definition missing descriptors array'));
    end

    descriptors = definition.descriptors;
    if (~iscell(descriptors) && ~isstruct(descriptors)) || isempty(descriptors)
        throw(MException(errorId, ...
            'Descriptor definition descriptors must be a non-empty array'));
    end

    descriptorNames = cell(1, numel(descriptors));
    requiredFields = {'name', 'formula', 'units', 'computation_method'};
    for descriptorIndex = 1:numel(descriptors)
        descriptor = get_descriptor(descriptors, descriptorIndex);
        if ~isstruct(descriptor) || ~isscalar(descriptor)
            throw(MException(errorId, ...
                'Descriptor definition entry %d must be a scalar object', ...
                descriptorIndex));
        end
        if ~isfield(descriptor, 'name')
            throw(MException(errorId, ...
                'Descriptor definition entry %d missing name field', ...
                descriptorIndex));
        end
        descriptorNames{descriptorIndex} = validate_text_scalar( ...
            descriptor.name, ...
            sprintf('Descriptor definition entry %d name', descriptorIndex), ...
            errorId);
        for fieldIndex = 1:numel(requiredFields)
            fieldName = requiredFields{fieldIndex};
            if ~isfield(descriptor, fieldName)
                throw(MException(errorId, ...
                    'Descriptor "%s" missing required field: %s', ...
                    descriptorNames{descriptorIndex}, fieldName));
            end
            validate_text_scalar(descriptor.(fieldName), ...
                sprintf('Descriptor "%s".%s', ...
                descriptorNames{descriptorIndex}, fieldName), errorId);
        end
    end

    if ~isequal(descriptorNames, configDescriptorNames)
        throw(MException(errorId, ...
            'Descriptor definition order [%s] does not match config order [%s]', ...
            strjoin(descriptorNames, ', '), strjoin(configDescriptorNames, ', ')));
    end
end

function descriptor = get_descriptor(descriptors, index)
    if iscell(descriptors)
        descriptor = descriptors{index};
    else
        descriptor = descriptors(index);
    end
end
