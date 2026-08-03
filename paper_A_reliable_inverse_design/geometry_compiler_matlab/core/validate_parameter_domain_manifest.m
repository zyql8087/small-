function validate_parameter_domain_manifest(manifest, errorId)
%VALIDATE_PARAMETER_DOMAIN_MANIFEST Validate the frozen Small domain schema.
    if ~isstruct(manifest) || ~isscalar(manifest)
        throw(MException(errorId, ...
            'parameter_domain_manifest must be a scalar JSON object'));
    end
    if ~isfield(manifest, 'schema_version')
        throw(MException(errorId, ...
            'parameter_domain_manifest.schema_version missing required field'));
    end
    schemaVersion = validate_text_scalar(manifest.schema_version, ...
        'parameter_domain_manifest.schema_version', errorId);
    if ~strcmp(schemaVersion, '1.0')
        throw(MException(errorId, ...
            'parameter_domain_manifest.schema_version must equal "1.0"'));
    end
    if ~isfield(manifest, 'methods')
        throw(MException(errorId, ...
            'parameter_domain_manifest.methods missing required field'));
    end
    methods = manifest.methods;
    if ~isstruct(methods) || ~isscalar(methods)
        throw(MException(errorId, ...
            'parameter_domain_manifest.methods must be a scalar object'));
    end

    methodNames = {'M1', 'M2', 'M3'};
    assert_field_set(methods, methodNames, ...
        'parameter_domain_manifest.methods', errorId);
    expectedVariables = struct( ...
        'M1', {{'c0', 'c1', 'c2'}}, ...
        'M2', {{'c_projected', 'w'}}, ...
        'M3', {{'c0', 'c1', 'c2', 'w'}});

    for methodIndex = 1:numel(methodNames)
        methodName = methodNames{methodIndex};
        method = methods.(methodName);
        methodLabel = sprintf('parameter_domain_manifest.methods.%s', methodName);
        if ~isstruct(method) || ~isscalar(method)
            throw(MException(errorId, '%s must be a scalar object', methodLabel));
        end
        if ~isfield(method, 'compiler_bounds')
            throw(MException(errorId, ...
                '%s.compiler_bounds missing required field', methodLabel));
        end
        bounds = method.compiler_bounds;
        boundsLabel = sprintf('%s.compiler_bounds', methodLabel);
        if ~isstruct(bounds) || ~isscalar(bounds)
            throw(MException(errorId, '%s must be a scalar object', boundsLabel));
        end
        assert_field_set(bounds, expectedVariables.(methodName), ...
            boundsLabel, errorId);
        variableNames = fieldnames(bounds)';
        for variableIndex = 1:numel(variableNames)
            variableName = variableNames{variableIndex};
            validate_bound(bounds.(variableName), ...
                sprintf('%s.%s', boundsLabel, variableName), errorId);
        end
    end
end

function validate_bound(bound, label, errorId)
    if ~isstruct(bound) || ~isscalar(bound)
        throw(MException(errorId, '%s must be a scalar object', label));
    end
    requiredFields = {'lower', 'upper', 'lower_inclusive', 'upper_inclusive'};
    assert_field_set(bound, requiredFields, label, errorId);
    if ~isnumeric(bound.lower) || ~isscalar(bound.lower) || ...
            ~isfinite(bound.lower) || ~isnumeric(bound.upper) || ...
            ~isscalar(bound.upper) || ~isfinite(bound.upper)
        throw(MException(errorId, ...
            '%s lower/upper must be finite numeric scalars', label));
    end
    if bound.lower > bound.upper
        throw(MException(errorId, '%s lower must be <= upper', label));
    end
    if ~islogical(bound.lower_inclusive) || ~isscalar(bound.lower_inclusive)
        throw(MException(errorId, ...
            '%s.lower_inclusive must be a logical scalar', label));
    end
    if ~islogical(bound.upper_inclusive) || ~isscalar(bound.upper_inclusive)
        throw(MException(errorId, ...
            '%s.upper_inclusive must be a logical scalar', label));
    end
end

function assert_field_set(value, expectedFields, label, errorId)
    actualFields = sort(fieldnames(value))';
    expectedFields = sort(expectedFields(:))';
    if ~isequal(actualFields, expectedFields)
        throw(MException(errorId, ...
            '%s must have fields {%s}, got {%s}', label, ...
            strjoin(expectedFields, ', '), strjoin(actualFields, ', ')));
    end
end
