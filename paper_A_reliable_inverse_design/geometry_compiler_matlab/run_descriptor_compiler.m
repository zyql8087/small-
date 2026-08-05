function response = run_descriptor_compiler(requestPath, m03ResponsePath, m04ResponsePath)
%RUN_DESCRIPTOR_COMPILER Compute authenticated dual M04 descriptors.

    baseDirectory = fileparts(mfilename('fullpath'));
    addpath(fullfile(baseDirectory, 'core'));
    m04ResponsePath = validate_text_scalar(m04ResponsePath, ...
        'm04_response_path', 'MATLABGyroid:InvalidRequest');
    if path_exists(m04ResponsePath)
        throw(MException('MATLABGyroid:OutputConflict', ...
            'refusing to overwrite M04 response JSON leaf: %s', m04ResponsePath));
    end
    outputDirectory = fileparts(m04ResponsePath);
    if isempty(outputDirectory)
        outputDirectory = pwd;
    end
    if exist(outputDirectory, 'dir') ~= 7
        throw(MException('MATLABGyroid:OutputConflict', ...
            'M04 response directory does not exist: %s', outputDirectory));
    end

    contract = compiler_contract();
    response = base_response(contract);
    createdManifest = '';
    request = [];
    try
        configPath = fullfile(baseDirectory, 'configs', ...
            'compiler_config.example.json');
        config = load_compiler_config(configPath);
        config.compiler_config_sha256 = sha256_file(configPath, ...
            'MATLABGyroid:InvalidConfig', 'compiler config');
        request = parse_and_validate_request(requestPath, config);
        response.request_id = request.request_id;

        authenticated = read_and_verify_m03_artifacts(request, ...
            m03ResponsePath, config);
        validatedMesh = rebuild_and_verify_m03_mesh(request, config, ...
            authenticated.stl_path);
        profiles = compute_descriptor_profiles(request.effective_parameters, ...
            config, request.resolution, validatedMesh, ...
            authenticated.physical_bounds_mm);
        canonicalText = canonical_descriptor_text(profiles);
        canonicalSha256 = sha256_text(canonicalText);

        manifestPath = descriptor_manifest_path(m04ResponsePath, ...
            authenticated.m03.geometry_identity_sha256);
        descriptorManifest = struct('schema_version', '1.0', ...
            'validation_stage', contract.descriptorValidationStage, ...
            'compiler_version', compiler_version(), ...
            'request_id', request.request_id, ...
            'm03_geometry_identity_sha256', ...
            authenticated.m03.geometry_identity_sha256, ...
            'm03_manifest_sha256', ...
            authenticated.m03.artifacts.manifest_sha256, ...
            'm03_stl_sha256', authenticated.m03.artifacts.stl_sha256, ...
            'descriptor_canonical_text', canonicalText, ...
            'descriptor_canonical_sha256', canonicalSha256, ...
            'descriptors', profiles);
        write_json_atomic(descriptorManifest, manifestPath);
        createdManifest = manifestPath;
        manifestSha256 = sha256_file(manifestPath, ...
            'MATLABGyroid:OutputError', 'published M04 descriptor manifest');

        response.valid = true;
        response.failure_code = '';
        response.failure_message = '';
        response.geometry_identity_sha256 = ...
            authenticated.m03.geometry_identity_sha256;
        response.descriptors = profiles;
        response.descriptor_canonical_sha256 = canonicalSha256;
        response.artifacts = struct('manifest_path', manifestPath, ...
            'manifest_sha256', manifestSha256, ...
            'm03_response_path', authenticated.response_path, ...
            'm03_manifest_path', authenticated.manifest_path, ...
            'm03_stl_path', authenticated.stl_path);
        write_json_atomic(response, m04ResponsePath);
    catch cause
        delete_owned_file(createdManifest);
        response.valid = false;
        response.failure_code = map_m04_failure_code(cause.identifier);
        response.failure_message = cause.message;
        if ~isempty(request)
            response.request_id = request.request_id;
        end
        if exist(m04ResponsePath, 'file') ~= 2
            write_json_atomic(response, m04ResponsePath);
        end
    end
end

function response = base_response(contract)
    response = struct('schema_version', '1.0', 'request_id', '', ...
        'compiler_version', compiler_version(), ...
        'validation_stage', contract.descriptorValidationStage, ...
        'valid', false, 'failure_code', '', 'failure_message', '', ...
        'geometry_identity_sha256', '', 'descriptors', struct(), ...
        'descriptor_canonical_sha256', '', 'artifacts', struct(), ...
        'abaqus_gate0', struct('status', 'not_run', 'solver_ready', false), ...
        'printability', 'not_computed', 'experiment', 'not_computed');
end

function mesh = rebuild_and_verify_m03_mesh(request, config, stlPath)
    errorId = 'MATLABGyroid:M03ArtifactMismatch';
    try
        contract = compiler_contract();
        field = build_finite_csg_field(request.effective_parameters, ...
            config, request.resolution, true);
        mesh = extract_isosurface_mesh(field, contract.isosurfaceLevel);
        [report, mesh] = validate_surface_mesh(mesh, field.spacing_mm, ...
            config.mesh_qc);
        if ~report.valid || field.solid_component_count ~= 1
            throw(MException(errorId, ...
                'reconstructed M03 geometry does not pass the M03 mesh gate'));
        end
        verify_binary_stl(stlPath, mesh);
    catch cause
        if strcmp(cause.identifier, errorId)
            rethrow(cause);
        end
        wrapped = MException(errorId, ...
            'M03 artifact rebuild or STL comparison failed: %s', cause.message);
        wrapped = addCause(wrapped, cause);
        throw(wrapped);
    end
end

function path = descriptor_manifest_path(responsePath, geometryHash)
    responseFile = javaObject('java.io.File', responsePath);
    responseCanonical = char(responseFile.getCanonicalPath());
    outputDirectory = fileparts(responseCanonical);
    responseDigest = sha256_text(responseCanonical);
    path = fullfile(outputDirectory, sprintf( ...
        'descriptor_%s_%s.manifest.json', geometryHash, responseDigest(1:16)));
end

function tf = path_exists(path)
    tf = exist(path, 'file') ~= 0 || exist(path, 'dir') ~= 0;
end

function delete_owned_file(path)
    if ~isempty(path) && exist(path, 'file') == 2
        delete(path);
    end
end
