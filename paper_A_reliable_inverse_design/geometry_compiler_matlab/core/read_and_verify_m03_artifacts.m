function authenticated = read_and_verify_m03_artifacts(request, m03ResponsePath, config)
%READ_AND_VERIFY_M03_ARTIFACTS Authenticate immutable M03 publication data.

    errorId = 'MATLABGyroid:M03ArtifactMismatch';
    m03ResponsePath = validate_text_scalar(m03ResponsePath, ...
        'm03_response_path', errorId);
    responsePath = canonical_existing_file(m03ResponsePath, '', errorId, ...
        'M03 response');
    try
        m03 = jsondecode(fileread(responsePath));
    catch cause
        throw_wrapped(errorId, 'M03 response JSON is unreadable', cause);
    end
    require_fields(m03, {'valid', 'request_id', 'compiler_version', ...
        'validation_stage', 'geometry_identity_sha256', 'artifacts'}, ...
        'M03 response', errorId);
    if ~islogical(m03.valid) || ~isscalar(m03.valid) || ~m03.valid
        throw(MException(errorId, 'M03 response must report valid=true'));
    end
    require_equal_text(m03.request_id, request.request_id, ...
        'M03 request identity', errorId);
    require_equal_text(m03.compiler_version, compiler_version(), ...
        'M03 compiler version', errorId);
    contract = compiler_contract();
    require_equal_text(m03.validation_stage, contract.validationStage, ...
        'M03 validation stage', errorId);
    geometryHash = validate_hash(m03.geometry_identity_sha256, ...
        'M03 geometry identity', errorId);

    artifacts = m03.artifacts;
    require_fields(artifacts, {'stl_path', 'manifest_path', 'stl_sha256', ...
        'manifest_sha256', 'stl_byte_length', 'triangle_count'}, ...
        'M03 artifacts', errorId);
    stlPath = resolve_embedded_file(artifacts.stl_path, responsePath, ...
        request.output_dir, errorId, 'M03 STL');
    manifestPath = resolve_embedded_file(artifacts.manifest_path, responsePath, ...
        request.output_dir, errorId, 'M03 manifest');
    require_equal_text(file_name(stlPath), ...
        sprintf('geometry_%s.stl', geometryHash), 'M03 STL filename', errorId);
    require_equal_text(file_name(manifestPath), ...
        sprintf('geometry_%s.manifest.json', geometryHash), ...
        'M03 manifest filename', errorId);
    stlSha256 = sha256_file(stlPath, errorId, 'M03 STL');
    require_equal_text(artifacts.stl_sha256, stlSha256, ...
        'M03 STL digest', errorId);
    manifestSha256 = sha256_file(manifestPath, errorId, 'M03 manifest');
    require_equal_text(artifacts.manifest_sha256, manifestSha256, ...
        'M03 manifest digest', errorId);
    stlSummary = verify_binary_stl(stlPath);
    require_equal_number(artifacts.stl_byte_length, stlSummary.byte_length, ...
        'M03 STL byte length', errorId);
    require_equal_number(artifacts.triangle_count, stlSummary.triangle_count, ...
        'M03 STL triangle count', errorId);

    try
        manifest = jsondecode(fileread(manifestPath));
    catch cause
        throw_wrapped(errorId, 'M03 manifest JSON is unreadable', cause);
    end
    require_fields(manifest, {'compiler_version', 'geometry_identity_sha256', ...
        'request', 'discretization', 'artifact'}, 'M03 manifest', errorId);
    require_equal_text(manifest.compiler_version, m03.compiler_version, ...
        'M03 manifest compiler version', errorId);
    require_equal_text(manifest.geometry_identity_sha256, geometryHash, ...
        'M03 manifest geometry identity', errorId);
    require_fields(manifest.request, {'request_id', 'raw_request_sha256', ...
        'request_semantic_sha256'}, 'M03 manifest request', errorId);
    require_equal_text(manifest.request.request_id, request.request_id, ...
        'M03 manifest request identity', errorId);
    require_equal_text(manifest.request.raw_request_sha256, ...
        request.raw_request_sha256, 'M03 request raw digest', errorId);
    require_equal_text(manifest.request.request_semantic_sha256, ...
        request.request_semantic_sha256, 'M03 request semantic digest', errorId);
    require_fields(manifest.artifact, {'sha256', 'byte_length', ...
        'triangle_count'}, 'M03 manifest artifact', errorId);
    require_equal_text(manifest.artifact.sha256, stlSha256, ...
        'M03 manifest STL digest', errorId);
    require_equal_number(manifest.artifact.byte_length, stlSummary.byte_length, ...
        'M03 manifest STL byte length', errorId);
    require_equal_number(manifest.artifact.triangle_count, stlSummary.triangle_count, ...
        'M03 manifest STL triangle count', errorId);
    boundsMm = verify_discretization(manifest.discretization, request, config, errorId);

    authenticated = struct('m03', m03, 'manifest', manifest, ...
        'response_path', responsePath, 'stl_path', stlPath, ...
        'manifest_path', manifestPath, 'stl_summary', stlSummary, ...
        'physical_bounds_mm', boundsMm);
end

function boundsMm = verify_discretization(discretization, request, config, errorId)
    require_fields(discretization, {'units', 'resolution', ...
        'reference_length_mm', 'physical_bounds_mm'}, ...
        'M03 discretization', errorId);
    require_equal_text(discretization.units, 'mm', 'M03 length unit', errorId);
    require_equal_number(discretization.resolution, request.resolution, ...
        'M03 resolution', errorId);
    require_equal_number(discretization.reference_length_mm, ...
        config.reference_length_mm, 'M03 reference length', errorId);
    physical = discretization.physical_bounds_mm;
    require_fields(physical, {'x', 'y', 'z'}, 'M03 physical bounds', errorId);
    domain = config.geometry_parameters.domain_over_l;
    expected = [double(domain.x(:)) .* config.reference_length_mm, ...
        double(domain.y(:)) .* config.reference_length_mm, ...
        double(domain.z(:)) .* config.reference_length_mm];
    boundsMm = zeros(3, 2);
    names = {'x', 'y', 'z'};
    for index = 1:numel(names)
        value = physical.(names{index});
        if ~isnumeric(value) || ~isreal(value) || numel(value) ~= 2 || ...
                any(~isfinite(value(:)))
            throw(MException(errorId, 'M03 physical bound %s is invalid', ...
                names{index}));
        end
        value = double(value(:));
        tolerance = 64 * eps(max(1, max(abs([value; expected(:, index)]))));
        if any(abs(value - expected(:, index)) > tolerance)
            throw(MException(errorId, ...
                'M03 physical bound %s conflicts with the active configuration', ...
                names{index}));
        end
        boundsMm(index, :) = value';
    end
end

function path = resolve_embedded_file(value, responsePath, outputDirectory, errorId, label)
    value = validate_text_scalar(value, [label, ' path'], errorId);
    if is_absolute_path(value)
        candidate = value;
    else
        candidate = fullfile(fileparts(responsePath), value);
    end
    path = canonical_existing_file(candidate, outputDirectory, errorId, label);
end

function path = canonical_existing_file(value, requiredParent, errorId, label)
    if exist(value, 'file') ~= 2 || exist(value, 'dir') == 7
        throw(MException(errorId, '%s must be an ordinary existing file', label));
    end
    path = canonical_path(value);
    if ~isempty(requiredParent) && ~is_within(path, canonical_path(requiredParent))
        throw(MException(errorId, '%s path escapes the request output directory', label));
    end
end

function tf = is_within(path, parent)
    if ispc
        path = lower(path);
        parent = lower(parent);
    end
    if ~endsWith(parent, filesep)
        parent = [parent, filesep];
    end
    tf = startsWith(path, parent);
end

function path = canonical_path(value)
    fileObject = javaObject('java.io.File', value);
    path = char(fileObject.getCanonicalPath());
end

function tf = is_absolute_path(path)
    if ispc
        tf = ~isempty(regexp(path, '^[A-Za-z]:[\\/]', 'once')) || ...
            startsWith(path, '\\');
    else
        tf = startsWith(path, '/');
    end
end

function value = file_name(path)
    [~, name, extension] = fileparts(path);
    value = [name, extension];
end

function require_fields(value, names, label, errorId)
    if ~isstruct(value) || ~isscalar(value) || ~all(isfield(value, names))
        throw(MException(errorId, '%s has missing or invalid fields', label));
    end
end

function require_equal_text(actual, expected, label, errorId)
    actual = validate_text_scalar(actual, label, errorId);
    expected = validate_text_scalar(expected, label, errorId);
    if ~strcmp(actual, expected)
        throw(MException(errorId, '%s does not match the active contract', label));
    end
end

function require_equal_number(actual, expected, label, errorId)
    if ~isnumeric(actual) || ~isscalar(actual) || ~isreal(actual) || ...
            ~isfinite(actual) || double(actual) ~= double(expected)
        throw(MException(errorId, '%s does not match the active contract', label));
    end
end

function value = validate_hash(value, label, errorId)
    value = validate_text_scalar(value, label, errorId);
    if isempty(regexp(value, '^[0-9a-f]{64}$', 'once'))
        throw(MException(errorId, '%s must be a lowercase SHA-256 digest', label));
    end
end

function throw_wrapped(errorId, message, cause)
    wrapped = MException(errorId, '%s: %s', message, cause.message);
    wrapped = addCause(wrapped, cause);
    throw(wrapped);
end
