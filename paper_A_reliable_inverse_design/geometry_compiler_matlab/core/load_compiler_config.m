function config = load_compiler_config(config_path)
%LOAD_COMPILER_CONFIG Loads and validates the MATLAB geometry compiler configuration
%   CONFIG = LOAD_COMPILER_CONFIG(CONFIG_PATH) loads a JSON configuration file
%   and validates it against the frozen compiler contract schema (v1.0).
%
%   All validation failures throw MException with identifier
%   'MATLABGyroid:InvalidConfig' so that downstream JSON failure-code
%   mapping can rely on a single error identifier.
%
%   Validated fields:
%       - schema_version        : must be exactly "1.0"
%       - reference_length_mm   : positive numeric scalar
%       - resolution            : positive integer (numeric, not string)
%       - descriptor_names      : cell array in fixed contract order
%       - descriptor_definition_path : relative path resolved against config dir
%       - solid_convention      : "sheet_band" (only allowed value at bootstrap)
%       - method_bounds         : struct with M1/M2/M3, named variable bounds,
%                                 active/fixed/projection rules, lower <= upper
%       - mesh_qc               : struct with mesh quality parameters
%       - geometry_parameters   : struct with Lx/Ly/Lz0 (positive finite) and units="mm"
%
%   The descriptor definition JSON is also validated for schema_version,
%   descriptor order consistency with the main config, and required fields.
%
%   See also: compiler_version

    ERROR_ID = 'MATLABGyroid:InvalidConfig';

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

    %% Validate required fields exist
    required_fields = {'schema_version', 'reference_length_mm', 'resolution', ...
        'descriptor_names', 'descriptor_definition_path', ...
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

    %% Validate resolution is a positive numeric integer (reject strings)
    if ~isnumeric(data.resolution) || ~isscalar(data.resolution)
        throw(MException(ERROR_ID, ...
            'Resolution must be a numeric scalar, got %s: %s', ...
            class(data.resolution), mat2str(data.resolution)));
    end
    if data.resolution <= 0 || mod(data.resolution, 1) ~= 0
        throw(MException(ERROR_ID, ...
            'Resolution must be a positive integer, got: %g', data.resolution));
    end

    %% Validate reference_length_mm is a positive numeric scalar (reject strings)
    if ~isnumeric(data.reference_length_mm) || ~isscalar(data.reference_length_mm)
        throw(MException(ERROR_ID, ...
            'reference_length_mm must be a numeric scalar, got %s', ...
            class(data.reference_length_mm)));
    end
    if data.reference_length_mm <= 0 || ~isfinite(data.reference_length_mm)
        throw(MException(ERROR_ID, ...
            'reference_length_mm must be a positive finite scalar, got: %g', data.reference_length_mm));
    end

    %% Validate method_bounds structure
    validate_method_bounds(data.method_bounds, ERROR_ID);

    %% Validate mesh_qc structure
    validate_mesh_qc(data.mesh_qc, ERROR_ID);

    %% Validate geometry_parameters structure
    gp = data.geometry_parameters;
    if ~isstruct(gp) || ~isscalar(gp)
        throw(MException(ERROR_ID, ...
            'geometry_parameters must be a scalar struct, got: %s', class(gp)));
    end
    gp_fields = {'Lx', 'Ly', 'Lz0', 'units'};
    for i = 1:length(gp_fields)
        if ~isfield(gp, gp_fields{i})
            throw(MException(ERROR_ID, ...
                'geometry_parameters missing required field: %s', gp_fields{i}));
        end
    end
    gp_numeric = {'Lx', 'Ly', 'Lz0'};
    for i = 1:length(gp_numeric)
        val = gp.(gp_numeric{i});
        if ~isnumeric(val) || ~isscalar(val) || val <= 0 || ~isfinite(val)
            throw(MException(ERROR_ID, ...
                'geometry_parameters.%s must be a positive finite numeric scalar', gp_numeric{i}));
        end
    end
    gp_units = char(string(gp.units));
    if ~strcmp(gp_units, 'mm')
        throw(MException(ERROR_ID, ...
            'geometry_parameters.units must be "mm", got: "%s"', gp_units));
    end

    %% Build configuration structure
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

    %% Resolve descriptor_definition_path relative to config file directory
    desc_path_rel = char(string(data.descriptor_definition_path));
    config.descriptor_definition_path = fullfile(config_dir, desc_path_rel);

    if exist(config.descriptor_definition_path, 'file') ~= 2
        throw(MException(ERROR_ID, ...
            'Descriptor definition not found at resolved path: %s', ...
            config.descriptor_definition_path));
    end

    %% Enforce fixed descriptor ordering (error, not warning)
    expected_order = {'relativeVolume', 'relativeArea', 'thickness', ...
                      'poreDiameter', 'areaMean'};
    config_desc = config.descriptor_names;
    if ~isequal(config_desc, expected_order)
        throw(MException(ERROR_ID, ...
            'Descriptor order mismatch. Expected: [%s], Got: [%s]', ...
            strjoin(expected_order, ', '), strjoin(config_desc, ', ')));
    end

    %% Validate descriptor definition JSON (schema + order consistency)
    validate_descriptor_definition(config.descriptor_definition_path, ...
        config.descriptor_names, ERROR_ID);

end

%% ========================================================================
%  Local validation helpers
%  ========================================================================

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

        % Required sub-fields for each method
        method_fields = {'active_variables', 'fixed_variables', 'bounds', 'levels', ...
            'convergence_tolerance', 'max_iterations'};
        for j = 1:length(method_fields)
            fname = method_fields{j};
            if ~isfield(m, fname)
                throw(MException(ERROR_ID, ...
                    'method_bounds.%s missing required field: %s', mname, fname));
            end
        end

        % Validate active_variables contains only legal variable names
        av = m.active_variables;
        if iscell(av)
            av_list = av;
        elseif ischar(av)
            av_list = cellstr(av);
        else
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.active_variables must be a string array', mname));
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
        % Each fixed variable value must be a finite numeric scalar
        fv_names = fieldnames(fv);
        for j = 1:length(fv_names)
            fval = fv.(fv_names{j});
            if ~isnumeric(fval) || ~isscalar(fval) || ~isfinite(fval)
                throw(MException(ERROR_ID, ...
                    'method_bounds.%s.fixed_variables.%s must be a finite numeric scalar', ...
                    mname, fv_names{j}));
            end
        end

        % Validate projection (optional: may be empty/null for M1/M3)
        if isfield(m, 'projection')
            proj = m.projection;
            if ~isempty(proj)
                if ~isstruct(proj) || ~isscalar(proj)
                    throw(MException(ERROR_ID, ...
                        'method_bounds.%s.projection must be a scalar struct or null', mname));
                end
                proj_fields = {'type', 'variables', 'projected_name'};
                for j = 1:length(proj_fields)
                    if ~isfield(proj, proj_fields{j})
                        throw(MException(ERROR_ID, ...
                            'method_bounds.%s.projection missing field: %s', mname, proj_fields{j}));
                    end
                end
            end
        end

        % Validate bounds is a struct with named variables
        bounds = m.bounds;
        if ~isstruct(bounds) || ~isscalar(bounds)
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.bounds must be a scalar struct with named variables, got: %s', ...
                mname, class(bounds)));
        end

        % Each bound variable must have numeric scalar lower and upper
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

        % Validate levels: non-empty, finite, unique, strictly increasing 1-D integer array
        levels = m.levels;
        if ~isnumeric(levels) || isempty(levels)
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.levels must be a non-empty numeric array', mname));
        end
        if ~isvector(levels)
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.levels must be a 1-D array', mname));
        end
        levels = levels(:)';  % normalise to row vector
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

        % Validate convergence_tolerance is a positive finite numeric scalar
        ct = m.convergence_tolerance;
        if ~isnumeric(ct) || ~isscalar(ct) || ct <= 0 || ~isfinite(ct)
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.convergence_tolerance must be a positive finite scalar', mname));
        end

        % Validate max_iterations is a positive finite integer
        mi = m.max_iterations;
        if ~isnumeric(mi) || ~isscalar(mi) || mi <= 0 || mod(mi, 1) ~= 0 || ~isfinite(mi)
            throw(MException(ERROR_ID, ...
                'method_bounds.%s.max_iterations must be a positive finite integer', mname));
        end
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

    % Numeric fields must be positive finite numeric scalars
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

    % Logical fields must be logical scalar (reject numeric 0/1)
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

    % Check schema_version
    if ~isfield(dd, 'schema_version')
        throw(MException(ERROR_ID, ...
            'Descriptor definition missing schema_version'));
    end
    dd_ver = char(string(dd.schema_version));
    if ~strcmp(dd_ver, '1.0')
        throw(MException(ERROR_ID, ...
            'Descriptor definition schema_version "%s" does not match frozen "1.0"', dd_ver));
    end

    % Check descriptors array exists
    if ~isfield(dd, 'descriptors')
        throw(MException(ERROR_ID, ...
            'Descriptor definition missing descriptors array'));
    end
    descs = dd.descriptors;
    if ~iscell(descs) && ~isstruct(descs)
        throw(MException(ERROR_ID, ...
            'Descriptor definition descriptors must be an array'));
    end

    % Extract descriptor names from definition in order
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
        % jsondecode may return struct array for JSON array of objects
        dd_names = cell(1, length(descs));
        for i = 1:length(descs)
            if ~isfield(descs(i), 'name')
                throw(MException(ERROR_ID, ...
                    'Descriptor definition entry %d missing name field', i));
            end
            dd_names{i} = char(string(descs(i).name));
        end
    end

    % Check order consistency with main config
    if ~isequal(dd_names, config_descriptor_names)
        throw(MException(ERROR_ID, ...
            'Descriptor definition order [%s] does not match config order [%s]', ...
            strjoin(dd_names, ', '), strjoin(config_descriptor_names, ', ')));
    end

    % Check each descriptor has required fields
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
