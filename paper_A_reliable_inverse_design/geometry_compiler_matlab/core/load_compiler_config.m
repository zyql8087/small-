function config = load_compiler_config(config_path)
%LOAD_COMPILER_CONFIG Loads and validates the MATLAB geometry compiler configuration
%   CONFIG = LOAD_COMPILER_CONFIG(CONFIG_PATH) loads a JSON configuration file
%   and validates it against the frozen compiler contract schema (v1.0).
%
%   All validation failures throw MException with identifier
%   'MATLABGyroid:InvalidConfig' so that downstream JSON failure-code
%   mapping can rely on a single error identifier.
%
%   See also: compiler_version, compiler_contract, sha256_file

    ERROR_ID = 'MATLABGyroid:InvalidConfig';

    %% Step 6: Validate public argument before exist
    if nargin ~= 1
        throw(MException(ERROR_ID, ...
            'load_compiler_config requires exactly one config_path argument'));
    end
    if ~(ischar(config_path) && isrow(config_path)) && ...
            ~(isstring(config_path) && isscalar(config_path))
        throw(MException(ERROR_ID, ...
            'config_path must be a character row vector or string scalar'));
    end
    config_path = char(config_path);

    if exist(config_path, 'file') ~= 2
        throw(MException(ERROR_ID, 'Configuration file not found: %s', config_path));
    end

    config_dir = fileparts(strrep(config_path, '\', '/'));
    try
        raw_json = fileread(config_path);
    catch ME_read
        throw(MException(ERROR_ID, ...
            'Cannot read configuration file "%s": %s', config_path, ME_read.message));
    end

    %% Parse JSON
    try
        data = jsondecode(raw_json);
    catch jqe
        throw(MException(ERROR_ID, ...
            'JSON parsing failed for configuration file: %s', jqe.message));
    end

    if ~isstruct(data)
        throw(MException(ERROR_ID, ...
            'Configuration root must be a JSON object, got: %s', class(data)));
    end

    %% Step 7: Validate required fields exist (including SHA-256 fields)
    required_fields = {'schema_version', 'reference_length_mm', 'resolution', ...
        'descriptor_names', 'descriptor_definition_path', ...
        'descriptor_definition_sha256', ...
        'parameter_domain_manifest_path', ...
        'parameter_domain_manifest_sha256', ...
        'solid_convention', 'method_bounds', 'mesh_qc', 'geometry_parameters'};

    for i = 1:length(required_fields)
        field_name = required_fields{i};
        if ~isfield(data, field_name) || isempty(data.(field_name))
            throw(MException(ERROR_ID, ...
                'Missing required configuration field: %s', field_name));
        end
    end

    %% Validate schema_version (frozen at "1.0")
    schema_ver = char(string(data.schema_version));
    if ~strcmp(schema_ver, '1.0')
        throw(MException(ERROR_ID, ...
            'Unsupported schema_version "%s". Frozen contract requires "1.0".', schema_ver));
    end

    %% Validate solid_convention (only 'sheet_band' allowed at bootstrap)
    solid_conv = char(string(data.solid_convention));
    if ~strcmp(solid_conv, 'sheet_band')
        throw(MException(ERROR_ID, ...
            'Invalid solid_convention "%s". Must be "sheet_band" at bootstrap.', solid_conv));
    end

    %% Step 8: Validate resolution without silent saturation
    if ~isnumeric(data.resolution) || ~isscalar(data.resolution)
        throw(MException(ERROR_ID, ...
            'Resolution must be a numeric scalar, got %s: %s', ...
            class(data.resolution), mat2str(data.resolution)));
    end
    if data.resolution <= 0 || mod(data.resolution, 1) ~= 0
        throw(MException(ERROR_ID, ...
            'Resolution must be a positive integer, got: %g', data.resolution));
    end
    if data.resolution > double(intmax('uint32'))
        throw(MException(ERROR_ID, ...
            'Resolution exceeds uint32 capacity: %.0f', data.resolution));
    end

    %% Validate reference_length_mm is a positive numeric scalar
    if ~isnumeric(data.reference_length_mm) || ~isscalar(data.reference_length_mm)
        throw(MException(ERROR_ID, ...
            'reference_length_mm must be a numeric scalar, got %s', ...
            class(data.reference_length_mm)));
    end
    if data.reference_length_mm <= 0 || ~isfinite(data.reference_length_mm)
        throw(MException(ERROR_ID, ...
            'reference_length_mm must be a positive finite scalar, got: %g', data.reference_length_mm));
    end

    %% Step 9: Resolve, read, hash, and parse both contract files
    % --- Descriptor definition ---
    desc_path_rel = char(string(data.descriptor_definition_path));
    validate_relative_path(desc_path_rel, 'descriptor_definition_path', ERROR_ID);
    desc_path = fullfile(config_dir, desc_path_rel);
    if exist(desc_path, 'file') ~= 2
        throw(MException(ERROR_ID, ...
            'Descriptor definition not found at resolved path: %s', desc_path));
    end
    declared_desc_hash = lower(char(string(data.descriptor_definition_sha256)));
    validate_hash_format(declared_desc_hash, 'descriptor_definition_sha256', ERROR_ID);
    actual_desc_hash = sha256_file(desc_path, ERROR_ID, 'descriptor definition');
    if ~strcmp(actual_desc_hash, declared_desc_hash)
        throw(MException(ERROR_ID, ...
            'descriptor_definition_sha256 mismatch: declared=%s actual=%s', ...
            declared_desc_hash, actual_desc_hash));
    end

    % --- Parameter domain manifest ---
    manifest_path_rel = char(string(data.parameter_domain_manifest_path));
    validate_relative_path(manifest_path_rel, 'parameter_domain_manifest_path', ERROR_ID);
    manifest_path = fullfile(config_dir, manifest_path_rel);
    if exist(manifest_path, 'file') ~= 2
        throw(MException(ERROR_ID, ...
            'Parameter-domain manifest not found at resolved path: %s', manifest_path));
    end
    declared_manifest_hash = lower(char(string(data.parameter_domain_manifest_sha256)));
    validate_hash_format(declared_manifest_hash, 'parameter_domain_manifest_sha256', ERROR_ID);
    actual_manifest_hash = sha256_file(manifest_path, ERROR_ID, 'parameter-domain manifest');
    if ~strcmp(actual_manifest_hash, declared_manifest_hash)
        throw(MException(ERROR_ID, ...
            'parameter_domain_manifest_sha256 mismatch: declared=%s actual=%s', ...
            declared_manifest_hash, actual_manifest_hash));
    end

    % Parse manifest for later use
    try
        manifest = jsondecode(fileread(manifest_path));
    catch ME_mp
        throw(MException(ERROR_ID, ...
            'Parameter-domain manifest JSON parsing failed: %s', ME_mp.message));
    end

    %% Validate method_bounds structure (generic shape checks)
    validate_method_bounds(data.method_bounds, ERROR_ID);

    %% Step 12: Exact method contract validation
    contract = compiler_contract();
    validate_exact_method_contract(data.method_bounds, manifest, ...
        contract.requiredLevels, ERROR_ID);

    %% Validate mesh_qc structure
    validate_mesh_qc(data.mesh_qc, ERROR_ID);

    %% Step 10: Validate geometry parameters exactly
    validate_geometry_parameters(data.geometry_parameters, ERROR_ID);

    %% Step 13: Build validated configuration structure
    config = struct();
    config.schema_version = schema_ver;
    config.reference_length_mm = double(data.reference_length_mm);
    config.resolution = uint32(data.resolution);
    config.solid_convention = solid_conv;

    %% Convert descriptor_names to row vector cell array of char
    if iscell(data.descriptor_names)
        config.descriptor_names = reshape(data.descriptor_names, 1, []);
    elseif ischar(data.descriptor_names)
        config.descriptor_names = cellstr(data.descriptor_names)';
    else
        config.descriptor_names = cellfun(@char, num2cell(data.descriptor_names), 'UniformOutput', false);
        config.descriptor_names = reshape(config.descriptor_names, 1, []);
    end

    config.method_bounds = data.method_bounds;
    config.mesh_qc = data.mesh_qc;
    config.geometry_parameters = data.geometry_parameters;

    %% Resolve paths
    config.descriptor_definition_path = desc_path;
    config.descriptor_definition_sha256 = declared_desc_hash;
    config.parameter_domain_manifest_path = manifest_path;
    config.parameter_domain_manifest_sha256 = declared_manifest_hash;
    config.parameter_domain = manifest;

    %% Enforce fixed descriptor ordering (error, not warning)
    expected_order = contract.descriptorNames;
    config_desc = config.descriptor_names;
    if ~isequal(config_desc, expected_order)
        throw(MException(ERROR_ID, ...
            'Descriptor order mismatch. Expected: [%s], Got: [%s]', ...
            strjoin(expected_order, ', '), strjoin(config_desc, ', ')));
    end

    %% Validate descriptor definition JSON (schema + order consistency)
    validate_descriptor_definition(desc_path, config.descriptor_names, ERROR_ID);

end

%% ========================================================================
%  Local validation helpers
%  ========================================================================

function validate_relative_path(p, label, ERROR_ID)
    if isAbsolutePath(p)
        throw(MException(ERROR_ID, ...
            '%s must be a relative path, got: %s', label, p));
    end
    parts = strsplit(strrep(p, '\', '/'), '/');
    for i = 1:numel(parts)
        if strcmp(parts{i}, '..')
            throw(MException(ERROR_ID, ...
                '%s must not contain ".." segments: %s', label, p));
        end
    end
end

function tf = isAbsolutePath(p)
    tf = false;
    if isempty(p), return; end
    if p(1) == '/' || p(1) == '\', tf = true; return; end
    if length(p) >= 2 && isletter(p(1)) && p(2) == ':', tf = true; end
end

function validate_hash_format(h, label, ERROR_ID)
    if ~ischar(h) || length(h) ~= 64 || isempty(regexp(h, '^[0-9a-f]{64}$', 'once'))
        throw(MException(ERROR_ID, ...
            '%s must be exactly 64 lowercase hexadecimal characters, got: %s', label, h));
    end
end

function validate_method_bounds(mb, ERROR_ID)
%VALIDATE_METHOD_BOUNDS Validates the method_bounds structure
    if ~isstruct(mb) || ~isscalar(mb)
        throw(MException(ERROR_ID, ...
            'method_bounds must be a scalar struct, got: %s', class(mb)));
    end

    required_methods = {'M1', 'M2', 'M3'};
    legal_vars = {'c0', 'c1', 'c2', 'w', 'c_projected'};

    for i = 1:length(required_methods)
        mname = required_methods{i};
        if ~isfield(mb, mname)
            throw(MException(ERROR_ID, ...
                'method_bounds missing required method: %s', mname));
        end
        m = mb.(mname);
        if ~isstruct(m) || ~isscalar(m)
            throw(MException(ERROR_ID, ...
                'method_bounds.%s must be a scalar struct, got: %s', mname, class(m)));
        end

        % Step 11: Required sub-fields including projection and bounds_manifest_method
        method_fields = {'active_variables', 'fixed_variables', 'projection', ...
            'bounds_manifest_method', 'bounds', 'levels', ...
            'convergence_tolerance', 'max_iterations'};
        for j = 1:length(method_fields)
            fname = method_fields{j};
            if ~isfield(m, fname)
                throw(MException(ERROR_ID, ...
                    '%s.%s missing required field in method_bounds', mname, fname));
            end
        end

        % Validate active_variables contains only legal variable names
        av = m.active_variables;
        if isstring(av)
            av_list = cellstr(av)';
        elseif iscell(av)
            av_list = av;
        elseif ischar(av)
            av_list = cellstr(av);
        else
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.active_variables must be a string/cell array', mname));
        end
        if isempty(av_list)
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.active_variables must not be empty', mname));
        end
        for j = 1:length(av_list)
            vname = char(string(av_list{j}));
            if ~ismember(vname, legal_vars)
                throw(MException(ERROR_ID, ...
                    'method_bounds.%s.active_variables contains illegal variable "%s". Legal: [%s]', ...
                    mname, vname, strjoin(legal_vars, ', ')));
            end
        end

        % Validate fixed_variables is present and is a struct
        fv = m.fixed_variables;
        if ~isstruct(fv)
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.fixed_variables must be a struct, got: %s', mname, class(fv)));
        end
        fv_names = fieldnames(fv);
        for j = 1:length(fv_names)
            fval = fv.(fv_names{j});
            if ~isnumeric(fval) || ~isscalar(fval) || ~isfinite(fval)
                throw(MException(ERROR_ID, ...
                    'method_bounds.%s.fixed_variables.%s must be a finite numeric scalar', ...
                    mname, fv_names{j}));
            end
        end

        % Validate projection field exists (Step 11); null/empty allowed for M1/M3
        proj = m.projection;
        if ~isempty(proj)
            if ~isstruct(proj) || ~isscalar(proj)
                throw(MException(ERROR_ID, ...
                    'method_bounds.%s.projection must be a scalar struct or null', mname));
            end
        end

        % Validate bounds is a struct with named variables
        bounds = m.bounds;
        if ~isstruct(bounds) || ~isscalar(bounds)
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.bounds must be a scalar struct with named variables, got: %s', ...
                mname, class(bounds)));
        end
        bound_names = fieldnames(bounds);
        if isempty(bound_names)
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.bounds must contain at least one named variable', mname));
        end
        for k = 1:length(bound_names)
            vname = bound_names{k};
            v = bounds.(vname);
            if ~isstruct(v) || ~isscalar(v)
                throw(MException(ERROR_ID, ...
                    'method_bounds.%s.bounds.%s must be a struct with lower/upper, got: %s', ...
                    mname, vname, class(v)));
            end
            if ~isfield(v, 'lower') || ~isfield(v, 'upper')
                throw(MException(ERROR_ID, ...
                    'method_bounds.%s.bounds.%s must have both lower and upper fields', ...
                    mname, vname));
            end
            lo = v.lower;
            hi = v.upper;
            if ~isnumeric(lo) || ~isscalar(lo) || ~isnumeric(hi) || ~isscalar(hi)
                throw(MException(ERROR_ID, ...
                    'method_bounds.%s.bounds.%s lower/upper must be numeric scalars', ...
                    mname, vname));
            end
            if ~isfinite(lo) || ~isfinite(hi)
                throw(MException(ERROR_ID, ...
                    'method_bounds.%s.bounds.%s lower/upper must be finite', ...
                    mname, vname));
            end
            if lo > hi
                throw(MException(ERROR_ID, ...
                    'method_bounds.%s.bounds.%s lower (%g) must be <= upper (%g)', ...
                    mname, vname, lo, hi));
            end
        end

        % Validate levels
        levels = m.levels;
        if ~isnumeric(levels) || isempty(levels)
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.levels must be a non-empty numeric array', mname));
        end
        if ~isvector(levels)
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.levels must be a 1-D array', mname));
        end
        levels = levels(:)';
        if ~all(isfinite(levels))
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.levels must contain only finite values', mname));
        end
        if any(mod(levels, 1) ~= 0) || any(levels <= 0)
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.levels must be positive integers', mname));
        end
        if length(unique(levels)) ~= length(levels)
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.levels must contain unique values', mname));
        end
        if any(diff(levels) <= 0)
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.levels must be strictly increasing', mname));
        end

        % Validate convergence_tolerance
        ct = m.convergence_tolerance;
        if ~isnumeric(ct) || ~isscalar(ct) || ct <= 0 || ~isfinite(ct)
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.convergence_tolerance must be a positive finite scalar', mname));
        end

        % Validate max_iterations
        mi = m.max_iterations;
        if ~isnumeric(mi) || ~isscalar(mi) || mi <= 0 || mod(mi, 1) ~= 0 || ~isfinite(mi)
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.max_iterations must be a positive finite integer', mname));
        end
    end
end

function validate_exact_method_contract(mb, manifest, requiredLevels, ERROR_ID)
%VALIDATE_EXACT_METHOD_CONTRACT Step 12: exact method contract enforcement

    % --- M1 ---
    assert_cellstr_exact(mb.M1.active_variables, {'c0','c1','c2'}, ...
        'M1.active_variables', ERROR_ID);
    assert_field_set(mb.M1.fixed_variables, {'w'}, ...
        'M1.fixed_variables', ERROR_ID);
    if mb.M1.fixed_variables.w ~= 0
        throw(MException(ERROR_ID, 'M1.fixed_variables.w must equal 0'));
    end
    assert_empty_projection(mb.M1.projection, 'M1.projection', ERROR_ID);
    assert_field_set(mb.M1.bounds, {'c0','c1','c2'}, 'M1.bounds', ERROR_ID);

    % --- M2 ---
    assert_cellstr_exact(mb.M2.active_variables, {'c_projected','w'}, ...
        'M2.active_variables', ERROR_ID);
    assert_field_set(mb.M2.fixed_variables, {}, 'M2.fixed_variables', ERROR_ID);
    validate_m2_projection(mb.M2.projection, ERROR_ID);
    assert_field_set(mb.M2.bounds, {'c_projected','w'}, 'M2.bounds', ERROR_ID);

    % --- M3 ---
    assert_cellstr_exact(mb.M3.active_variables, {'c0','c1','c2','w'}, ...
        'M3.active_variables', ERROR_ID);
    assert_field_set(mb.M3.fixed_variables, {}, 'M3.fixed_variables', ERROR_ID);
    assert_empty_projection(mb.M3.projection, 'M3.projection', ERROR_ID);
    assert_field_set(mb.M3.bounds, {'c0','c1','c2','w'}, ...
        'M3.bounds', ERROR_ID);

    % --- Cross-method checks ---
    names = {'M1','M2','M3'};
    for i = 1:numel(names)
        name = names{i};
        if ~strcmp(char(string(mb.(name).bounds_manifest_method)), name)
            throw(MException(ERROR_ID, ...
                '%s.bounds_manifest_method must equal %s', name, name));
        end
        levels = double(mb.(name).levels(:)');
        if ~all(ismember(requiredLevels, levels))
            throw(MException(ERROR_ID, ...
                '%s.levels must contain [96, 128, 160]', name));
        end
        validate_bounds_match_manifest(mb.(name).bounds, ...
            manifest.methods.(name).compiler_bounds, name, ERROR_ID);
    end
end

function assert_cellstr_exact(actual, expected, label, ERROR_ID)
%ASSERT_CELLSTR_EXACT Compare cell-string sequences exactly, reject duplicates.
    if isstring(actual)
        actual = cellstr(actual)';
    elseif ischar(actual)
        actual = {actual};
    end
    if ~iscell(actual)
        throw(MException(ERROR_ID, '%s must be a cell/string array of strings', label));
    end
    actual = actual(:)';  % normalize to row vector
    actual_strs = cellfun(@(x) char(string(x)), actual, 'UniformOutput', false);
    if length(unique(actual_strs)) ~= length(actual_strs)
        throw(MException(ERROR_ID, '%s contains duplicates', label));
    end
    if ~isequal(actual_strs, expected)
        throw(MException(ERROR_ID, ...
            '%s must be [%s], got [%s]', label, ...
            strjoin(expected, ', '), strjoin(actual_strs, ', ')));
    end
end

function assert_field_set(s, requiredNames, label, ERROR_ID)
%ASSERT_FIELD_SET Compare struct field names as sets (order irrelevant).
    if ~isstruct(s)
        throw(MException(ERROR_ID, '%s must be a struct', label));
    end
    actual = sort(fieldnames(s))';
    expected = sort(requiredNames(:))';
    if ~isequal(actual, expected)
        throw(MException(ERROR_ID, ...
            '%s must have fields {%s}, got {%s}', label, ...
            strjoin(expected, ', '), strjoin(actual, ', ')));
    end
end

function assert_empty_projection(proj, label, ERROR_ID)
%ASSERT_EMPTY_PROJECTION M1/M3 must have null/empty projection.
    if ~isempty(proj)
        throw(MException(ERROR_ID, ...
            '%s must be null/empty for this method', label));
    end
end

function validate_m2_projection(proj, ERROR_ID)
%VALIDATE_M2_PROJECTION Exact M2 projection contract.
    if isempty(proj)
        throw(MException(ERROR_ID, 'M2.projection must not be empty'));
    end
    if ~isstruct(proj) || ~isscalar(proj)
        throw(MException(ERROR_ID, 'M2.projection must be a scalar struct'));
    end
    if ~isfield(proj, 'type') || ~strcmp(char(string(proj.type)), ...
            'orthogonal_l2_equal_subspace')
        throw(MException(ERROR_ID, ...
            'M2.projection.type must be orthogonal_l2_equal_subspace'));
    end
    if ~isfield(proj, 'variables')
        throw(MException(ERROR_ID, 'M2.projection.variables missing'));
    end
    vars = proj.variables;
    if isstring(vars), vars = cellstr(vars)'; end
    if ischar(vars), vars = {vars}; end
    vars = vars(:)';  % normalize to row
    var_strs = cellfun(@(x) char(string(x)), vars, 'UniformOutput', false);
    if ~isequal(var_strs, {'c0','c1','c2'})
        throw(MException(ERROR_ID, ...
            'M2.projection.variables must be [c0, c1, c2]'));
    end
    if ~isfield(proj, 'projected_name') || ...
            ~strcmp(char(string(proj.projected_name)), 'c_projected')
        throw(MException(ERROR_ID, ...
            'M2.projection.projected_name must be c_projected'));
    end
    expected_formula = 'c_projected=mean([c0,c1,c2]); c0=c1=c2=c_projected';
    if ~isfield(proj, 'formula') || ...
            ~strcmp(char(string(proj.formula)), expected_formula)
        throw(MException(ERROR_ID, ...
            'M2.projection.formula must be "%s"', expected_formula));
    end
end

function validate_bounds_match_manifest(bounds, manifest_bounds, mname, ERROR_ID)
%VALIDATE_BOUNDS_MATCH_MANIFEST Compare config bounds to manifest compiler_bounds.
    for vname = fieldnames(bounds)'
        vname = vname{1};
        b = bounds.(vname);
        if ~isfield(manifest_bounds, vname)
            continue; % manifest may not have all variables
        end
        mb = manifest_bounds.(vname);
        if b.lower ~= mb.lower || b.upper ~= mb.upper
            throw(MException(ERROR_ID, ...
                '%s.bounds.%s must match manifest [%g,%g], got [%g,%g]', ...
                mname, vname, mb.lower, mb.upper, b.lower, b.upper));
        end
        if isfield(b, 'lower_inclusive') && isfield(mb, 'lower_inclusive')
            if logical(b.lower_inclusive) ~= logical(mb.lower_inclusive)
                throw(MException(ERROR_ID, ...
                    '%s.bounds.%s.lower_inclusive must match manifest', mname, vname));
            end
        end
        if isfield(b, 'upper_inclusive') && isfield(mb, 'upper_inclusive')
            if logical(b.upper_inclusive) ~= logical(mb.upper_inclusive)
                throw(MException(ERROR_ID, ...
                    '%s.bounds.%s.upper_inclusive must match manifest', mname, vname));
            end
        end
    end
end

function validate_geometry_parameters(gp, ERROR_ID)
%VALIDATE_GEOMETRY_PARAMETERS Step 10: exact geometry parameter contract.
    if ~isstruct(gp) || ~isscalar(gp)
        throw(MException(ERROR_ID, ...
            'geometry_parameters must be a scalar struct, got: %s', class(gp)));
    end

    required_gp = {'coordinate_units', 'output_units', 'Lx_over_l', 'Ly_over_l', ...
        'Lz0_over_l', 'domain_over_l', 'w_units', 'cell_size_profile', ...
        'physical_conversion', 'validation_status'};
    for i = 1:numel(required_gp)
        if ~isfield(gp, required_gp{i})
            throw(MException(ERROR_ID, ...
                'geometry_parameters missing required field: %s', required_gp{i}));
        end
    end

    % String equality checks
    assert_gp_string(gp, 'coordinate_units', 'normalized_by_reference_length', ERROR_ID);
    assert_gp_string(gp, 'output_units', 'mm', ERROR_ID);
    assert_gp_string(gp, 'w_units', 'normalized_denominator_parameter', ERROR_ID);
    assert_gp_string(gp, 'cell_size_profile', 'gamma(z)=1.5+z/w', ERROR_ID);
    assert_gp_string(gp, 'validation_status', 'candidate_pending_gate0', ERROR_ID);

    % Numeric equality checks
    if gp.Lx_over_l ~= 1.0
        throw(MException(ERROR_ID, 'geometry_parameters.Lx_over_l must equal 1.0'));
    end
    if gp.Ly_over_l ~= 1.0
        throw(MException(ERROR_ID, 'geometry_parameters.Ly_over_l must equal 1.0'));
    end
    if gp.Lz0_over_l ~= 1.5
        throw(MException(ERROR_ID, 'geometry_parameters.Lz0_over_l must equal 1.5'));
    end

    % Domain vectors
    validate_domain_vector(gp.domain_over_l, 'x', [0, 1], ERROR_ID);
    validate_domain_vector(gp.domain_over_l, 'y', [0, 1], ERROR_ID);
    validate_domain_vector(gp.domain_over_l, 'z', [0, 2], ERROR_ID);
end

function assert_gp_string(gp, field, expected, ERROR_ID)
    actual = char(string(gp.(field)));
    if ~strcmp(actual, expected)
        throw(MException(ERROR_ID, ...
            'geometry_parameters.%s must be "%s", got "%s"', field, expected, actual));
    end
end

function validate_domain_vector(domain, axis, expected, ERROR_ID)
    if ~isfield(domain, axis)
        throw(MException(ERROR_ID, ...
            'geometry_parameters.domain_over_l missing field: %s', axis));
    end
    v = domain.(axis);
    if ~isnumeric(v) || any(~isfinite(v(:))) || numel(v) ~= 2
        throw(MException(ERROR_ID, ...
            'geometry_parameters.domain_over_l.%s must be a 2-element finite numeric vector', axis));
    end
    v = v(:)';
    if v(1) >= v(2)
        throw(MException(ERROR_ID, ...
            'geometry_parameters.domain_over_l.%s must be strictly increasing', axis));
    end
    if ~isequal(v, expected)
        throw(MException(ERROR_ID, ...
            'geometry_parameters.domain_over_l.%s must be [%g, %g], got [%g, %g]', ...
            axis, expected(1), expected(2), v(1), v(2)));
    end
end

function validate_mesh_qc(mq, ERROR_ID)
%VALIDATE_MESH_QC Validates the mesh_qc structure
    if ~isstruct(mq) || ~isscalar(mq)
        throw(MException(ERROR_ID, ...
            'mesh_qc must be a scalar struct, got: %s', class(mq)));
    end

    qc_fields = {'min_edge_length_ratio', 'max_angle_deviations', ...
        'surface_tolerance_mm', 'self_intersect_check', 'watertight_enforced'};
    for i = 1:length(qc_fields)
        fname = qc_fields{i};
        if ~isfield(mq, fname)
            throw(MException(ERROR_ID, ...
                'mesh_qc missing required field: %s', fname));
        end
    end

    numeric_fields = {'min_edge_length_ratio', 'max_angle_deviations', 'surface_tolerance_mm'};
    for i = 1:length(numeric_fields)
        fname = numeric_fields{i};
        val = mq.(fname);
        if ~isnumeric(val) || ~isscalar(val) || val <= 0 || ~isfinite(val)
            throw(MException(ERROR_ID, ...
                'mesh_qc.%s must be a positive finite numeric scalar, got: %s', ...
                fname, class(val)));
        end
    end

    logical_fields = {'self_intersect_check', 'watertight_enforced'};
    for i = 1:length(logical_fields)
        fname = logical_fields{i};
        val = mq.(fname);
        if ~islogical(val) || ~isscalar(val)
            throw(MException(ERROR_ID, ...
                'mesh_qc.%s must be a logical scalar (true/false), got: %s', fname, class(val)));
        end
    end
end

function validate_descriptor_definition(desc_path, config_descriptor_names, ERROR_ID)
%VALIDATE_DESCRIPTOR_DEFINITION Validates the descriptor definition JSON
    raw = fileread(desc_path);
    try
        dd = jsondecode(raw);
    catch jqe
        throw(MException(ERROR_ID, ...
            'Descriptor definition JSON parsing failed: %s', jqe.message));
    end

    if ~isstruct(dd)
        throw(MException(ERROR_ID, ...
            'Descriptor definition root must be a JSON object'));
    end

    if ~isfield(dd, 'schema_version')
        throw(MException(ERROR_ID, ...
            'Descriptor definition missing schema_version'));
    end
    dd_ver = char(string(dd.schema_version));
    if ~strcmp(dd_ver, '1.0')
        throw(MException(ERROR_ID, ...
            'Descriptor definition schema_version "%s" does not match frozen "1.0"', dd_ver));
    end

    if ~isfield(dd, 'descriptors')
        throw(MException(ERROR_ID, ...
            'Descriptor definition missing descriptors array'));
    end
    descs = dd.descriptors;
    if ~iscell(descs) && ~isstruct(descs)
        throw(MException(ERROR_ID, ...
            'Descriptor definition descriptors must be an array'));
    end

    if iscell(descs)
        dd_names = cell(1, length(descs));
        for i = 1:length(descs)
            if ~isfield(descs{i}, 'name')
                throw(MException(ERROR_ID, ...
                    'Descriptor definition entry %d missing name field', i));
            end
            dd_names{i} = char(string(descs{i}.name));
        end
    else
        dd_names = cell(1, length(descs));
        for i = 1:length(descs)
            if ~isfield(descs(i), 'name')
                throw(MException(ERROR_ID, ...
                    'Descriptor definition entry %d missing name field', i));
            end
            dd_names{i} = char(string(descs(i).name));
        end
    end

    if ~isequal(dd_names, config_descriptor_names)
        throw(MException(ERROR_ID, ...
            'Descriptor definition order [%s] does not match config order [%s]', ...
            strjoin(dd_names, ', '), strjoin(config_descriptor_names, ', ')));
    end

    required_desc_fields = {'name', 'formula', 'units', 'computation_method'};
    for i = 1:length(descs)
        if iscell(descs)
            d = descs{i};
        else
            d = descs(i);
        end
        for j = 1:length(required_desc_fields)
            fname = required_desc_fields{j};
            if ~isfield(d, fname)
                throw(MException(ERROR_ID, ...
                    'Descriptor "%s" missing required field: %s', dd_names{i}, fname));
            end
        end
    end
end
