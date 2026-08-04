function request = parse_and_validate_request(requestPath, config)
%PARSE_AND_VALIDATE_REQUEST Parse the strict public M03 request boundary.

    errorId = 'MATLABGyroid:InvalidRequest';
    requestPath = validate_text_scalar( ...
        requestPath, 'request_path', errorId);
    if exist(requestPath, 'file') ~= 2
        throw(MException(errorId, ...
            'request JSON not found: %s', requestPath));
    end
    rawRequestHash = sha256_file( ...
        requestPath, errorId, 'request JSON');
    try
        data = jsondecode(fileread(requestPath));
    catch cause
        wrapped = MException(errorId, ...
            'request JSON parsing failed: %s', cause.message);
        wrapped = addCause(wrapped, cause);
        throw(wrapped);
    end
    if ~isstruct(data) || ~isscalar(data)
        throw(MException(errorId, ...
            'request root must be a scalar JSON object'));
    end
    contract = compiler_contract();
    actualFields = sort(fieldnames(data));
    expectedFields = sort(contract.requestFields(:));
    if ~isequal(actualFields, expectedFields)
        throw(MException(errorId, ...
            'request must have exactly fields {%s}', ...
            strjoin(contract.requestFields, ', ')));
    end
    schemaVersion = validate_text_scalar( ...
        data.schema_version, 'schema_version', errorId);
    if ~strcmp(schemaVersion, contract.requestSchemaVersion)
        throw(MException(errorId, ...
            'schema_version must be "%s"', contract.requestSchemaVersion));
    end
    requestId = validate_text_scalar( ...
        data.request_id, 'request_id', errorId);
    if isempty(regexp(requestId, ...
            '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$', 'once'))
        throw(MException(errorId, ...
            'request_id must match [A-Za-z0-9][A-Za-z0-9._-]{0,127}'));
    end
    method = validate_text_scalar(data.method, 'method', errorId);
    numericNames = {'c0', 'c1', 'c2', 'w', 'resolution'};
    for valueIndex = 1:numel(numericNames)
        name = numericNames{valueIndex};
        value = data.(name);
        if ~isnumeric(value) || ~isscalar(value) || ~isreal(value) || ...
                ~isfinite(value)
            throw(MException(errorId, ...
                '%s must be a finite real numeric scalar', name));
        end
    end
    if data.resolution <= 0 || mod(data.resolution, 1) ~= 0
        throw(MException(errorId, ...
            'resolution must be a positive integer'));
    end
    if ~isfield(config, 'method_bounds') || ...
            ~isfield(config.method_bounds, method) || ...
            ~isfield(config.method_bounds.(method), 'levels') || ...
            ~ismember(double(data.resolution), ...
            double(config.method_bounds.(method).levels(:)'))
        throw(MException(errorId, ...
            'resolution must be a configured production level for %s', method));
    end
    requestedParameters = struct('c0', double(data.c0), ...
        'c1', double(data.c1), 'c2', double(data.c2), ...
        'w', double(data.w));
    effectiveParameters = project_method_constraints( ...
        method, requestedParameters, config);
    outputText = validate_text_scalar( ...
        data.output_dir, 'output_dir', errorId);
    if isempty(outputText)
        throw(MException(errorId, 'output_dir must not be empty'));
    end
    if is_absolute_path(outputText)
        outputDirectory = canonical_path(outputText);
    else
        outputDirectory = canonical_path(fullfile( ...
            fileparts(requestPath), outputText));
    end
    canonicalText = sprintf([ ...
        'schema_version=%s\nmethod=%s\nc0=%.17g\nc1=%.17g\n' ...
        'c2=%.17g\nw=%.17g\nresolution=%d\n'], ...
        schemaVersion, method, double(data.c0), double(data.c1), ...
        double(data.c2), double(data.w), double(data.resolution));

    request = struct();
    request.schema_version = schemaVersion;
    request.request_id = requestId;
    request.method = method;
    request.requested_parameters = requestedParameters;
    request.effective_parameters = effectiveParameters;
    request.resolution = double(data.resolution);
    request.output_dir = outputDirectory;
    request.request_path = canonical_path(requestPath);
    request.raw_request_sha256 = rawRequestHash;
    request.request_semantic_sha256 = sha256_text(canonicalText);
    request.canonical_semantic_text = canonicalText;
end

function tf = is_absolute_path(path)
    if ispc
        tf = ~isempty(regexp(path, '^[A-Za-z]:[\\/]', 'once')) || ...
            startsWith(path, '\\');
    else
        tf = startsWith(path, '/');
    end
end

function path = canonical_path(value)
    fileObject = javaObject('java.io.File', value);
    path = char(fileObject.getCanonicalPath());
end
