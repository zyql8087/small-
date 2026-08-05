function validate_descriptor_result(result, expectedProfile, expectedHash)
%VALIDATE_DESCRIPTOR_RESULT Enforce the shared finite descriptor envelope.

    errorId = 'MATLABGyroid:DescriptorProfileInvalid';
    expectedNames = {'relativeVolume', 'relativeArea', 'thickness', ...
        'poreDiameter', 'areaMean'};
    required = {'profile', 'definition_sha256', 'sampling', 'units', ...
        'values', 'diagnostics'};
    if ~isstruct(result) || ~isscalar(result) || ~all(isfield(result, required))
        throw(MException(errorId, 'descriptor result envelope is incomplete'));
    end
    if ~strcmp(validate_text_scalar(result.profile, 'profile', errorId), ...
            validate_text_scalar(expectedProfile, 'expected_profile', errorId))
        throw(MException('MATLABGyroid:DescriptorContractMismatch', ...
            'descriptor profile does not match the requested profile'));
    end
    actualHash = validate_lower_sha256(result.definition_sha256, ...
        'definition_sha256', errorId);
    expectedHash = validate_lower_sha256(expectedHash, ...
        'expected_hash', errorId);
    if ~strcmp(actualHash, expectedHash)
        throw(MException('MATLABGyroid:DescriptorContractMismatch', ...
            'descriptor definition hash does not match the active contract'));
    end
    if ~isstruct(result.sampling) || ~isscalar(result.sampling) || ...
            ~isstruct(result.units) || ~isscalar(result.units) || ...
            ~isstruct(result.values) || ~isscalar(result.values) || ...
            ~isstruct(result.diagnostics) || ~isscalar(result.diagnostics)
        throw(MException(errorId, 'descriptor result nested fields must be objects'));
    end
    if ~isequal(sort(fieldnames(result.values))', sort(expectedNames))
        throw(MException(errorId, ...
            'descriptor result values must contain exactly the five descriptors'));
    end
    if ~isequal(sort(fieldnames(result.units))', sort(expectedNames))
        throw(MException(errorId, ...
            'descriptor result units must contain exactly the five descriptors'));
    end
    expectedUnits = expected_units(char(result.profile));
    for index = 1:numel(expectedNames)
        name = expectedNames{index};
        value = result.values.(name);
        if ~isnumeric(value) || ~isscalar(value) || ~isreal(value) || ...
                ~isfinite(value)
            throw(MException('MATLABGyroid:DescriptorNonfinite', ...
                'descriptor %s must be a finite real scalar', name));
        end
        unit = validate_text_scalar(result.units.(name), ...
            sprintf('units.%s', name), errorId);
        if ~strcmp(unit, expectedUnits.(name))
            throw(MException(errorId, ...
                'descriptor unit %s does not match profile %s', ...
                name, result.profile));
        end
    end
end

function value = validate_lower_sha256(value, label, errorId)
    value = validate_text_scalar(value, label, errorId);
    if isempty(regexp(value, '^[0-9a-f]{64}$', 'once'))
        throw(MException(errorId, ...
            '%s must be 64 lowercase hexadecimal characters', label));
    end
end

function units = expected_units(profile)
    units = struct('relativeVolume', 'dimensionless', ...
        'thickness', 'mm', 'poreDiameter', 'mm', 'areaMean', 'mm2');
    switch profile
        case 'legacy_small'
            units.relativeArea = 'dimensionless';
        case 'physical_m04'
            units.relativeArea = 'mm^-1';
        otherwise
            throw(MException('MATLABGyroid:DescriptorProfileInvalid', ...
                'unsupported descriptor profile: %s', profile));
    end
end
