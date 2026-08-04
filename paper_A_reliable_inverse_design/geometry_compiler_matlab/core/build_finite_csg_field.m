function field = build_finite_csg_field( ...
        projected, config, resolution, enforceAllowedLevel)
%BUILD_FINITE_CSG_FIELD Build the staggered continuous hard-box CSG field.

    errorId = 'MATLABGyroid:InvalidGeometry';
    if nargin == 3
        enforceAllowedLevel = true;
    elseif nargin ~= 4
        throw(MException('MATLABGyroid:InvalidRequest', ...
            'build_finite_csg_field requires 3 or 4 inputs'));
    end
    if ~islogical(enforceAllowedLevel) || ~isscalar(enforceAllowedLevel)
        throw(MException(errorId, ...
            'enforce_allowed_level must be a logical scalar'));
    end
    method = get_method(projected);
    validate_resolution(resolution, method, config, ...
        enforceAllowedLevel, errorId);
    resolution = double(resolution);
    domain = get_domain(config, errorId);
    hOverL = 1 / resolution;
    xOverL = make_staggered_axis(domain.x, resolution, 'x', errorId);
    yOverL = make_staggered_axis(domain.y, resolution, 'y', errorId);
    zOverL = make_staggered_axis(domain.z, resolution, 'z', errorId);

    sample = evaluate_continuous_graded_gyroid(projected, config, ...
        xOverL, yOverL, zOverL);
    fSheet = abs(sample.G) - reshape(sample.threshold, 1, 1, []);
    xBox = max(domain.x(1) - reshape(xOverL, [], 1, 1), ...
        reshape(xOverL, [], 1, 1) - domain.x(2));
    yBox = max(domain.y(1) - reshape(yOverL, 1, [], 1), ...
        reshape(yOverL, 1, [], 1) - domain.y(2));
    zBox = max(domain.z(1) - reshape(zOverL, 1, 1, []), ...
        reshape(zOverL, 1, 1, []) - domain.z(2));
    fBox = max(max(xBox, yBox), zBox);
    contract = compiler_contract();
    F = compose_hard_box_csg(fSheet, fBox, contract.betaBox);
    if any(~isfinite(F(:)))
        throw(MException('MATLABGyroid:NonfiniteField', ...
            'finite CSG field contains non-finite values'));
    end

    xInterior = xOverL > domain.x(1) & xOverL < domain.x(2);
    yInterior = yOverL > domain.y(1) & yOverL < domain.y(2);
    zInterior = zOverL > domain.z(1) & zOverL < domain.z(2);
    interiorSolid = F(xInterior, yInterior, zInterior) <= 0;
    solidCount = nnz(interiorSolid);
    voidCount = numel(interiorSolid) - solidCount;
    if solidCount == 0
        throw(MException('MATLABGyroid:EmptySolid', ...
            'finite CSG field contains no interior solid cells'));
    end
    if voidCount == 0
        throw(MException('MATLABGyroid:FullSolid', ...
            'finite CSG field contains no interior void cells'));
    end
    solidComponents = bwconncomp(interiorSolid, 26);
    if ~outer_planes_are_positive(F)
        throw(MException(errorId, ...
            'finite CSG exterior sampling planes must be strictly positive'));
    end

    referenceLength = double(config.reference_length_mm);
    field = struct();
    field.method = method;
    field.resolution = resolution;
    field.x_over_l = xOverL;
    field.y_over_l = yOverL;
    field.z_over_l = zOverL;
    field.x_mm = xOverL .* referenceLength;
    field.y_mm = yOverL .* referenceLength;
    field.z_mm = zOverL .* referenceLength;
    field.spacing_over_l = hOverL;
    field.spacing_mm = hOverL .* referenceLength;
    field.exterior_margin_mm = 0.5 .* hOverL .* referenceLength;
    field.F = F;
    field.interior_solid_count = solidCount;
    field.interior_void_count = voidCount;
    field.interior_cell_count = numel(interiorSolid);
    field.interior_solid_fraction = solidCount ./ numel(interiorSolid);
    field.solid_connectivity = 26;
    field.solid_component_count = solidComponents.NumObjects;
    field.geometry_definition = contract.geometryDefinition;
    field.grid_convention = contract.gridConvention;
    field.beta_box = contract.betaBox;
    field.isosurface_level = contract.isosurfaceLevel;
end

function method = get_method(projected)
    if ~isstruct(projected) || ~isscalar(projected) || ...
            ~isfield(projected, 'method')
        throw(MException('MATLABGyroid:InvalidRequest', ...
            'projected parameters must be a scalar struct with method'));
    end
    method = validate_text_scalar(projected.method, 'projected.method', ...
        'MATLABGyroid:InvalidRequest');
    if ~ismember(method, {'M1', 'M2', 'M3'})
        throw(MException('MATLABGyroid:InvalidRequest', ...
            'projected.method must be one of {M1, M2, M3}'));
    end
end

function validate_resolution(value, method, config, enforce, errorId)
    if ~isnumeric(value) || ~isscalar(value) || ~isreal(value) || ...
            ~isfinite(value) || value <= 0 || mod(value, 1) ~= 0
        throw(MException(errorId, ...
            'resolution must be a finite positive integer'));
    end
    if ~isstruct(config) || ~isscalar(config) || ...
            ~isfield(config, 'method_bounds') || ...
            ~isfield(config.method_bounds, method) || ...
            ~isfield(config.method_bounds.(method), 'levels')
        throw(MException(errorId, ...
            'config does not contain method resolution levels'));
    end
    levels = double(config.method_bounds.(method).levels(:)');
    if value > max(levels)
        throw(MException(errorId, ...
            'resolution exceeds the configured method maximum'));
    end
    if enforce && ~ismember(double(value), levels)
        throw(MException(errorId, ...
            'resolution must be one of the configured levels for %s', method));
    end
end

function domain = get_domain(config, errorId)
    if ~isstruct(config) || ~isscalar(config) || ...
            ~isfield(config, 'geometry_parameters') || ...
            ~isstruct(config.geometry_parameters) || ...
            ~isscalar(config.geometry_parameters) || ...
            ~isfield(config.geometry_parameters, 'domain_over_l') || ...
            ~isfield(config, 'reference_length_mm')
        throw(MException(errorId, ...
            'config does not contain the finite geometry contract'));
    end
    domain = config.geometry_parameters.domain_over_l;
    if ~isstruct(domain) || ~isscalar(domain) || ...
            ~all(isfield(domain, {'x', 'y', 'z'}))
        throw(MException(errorId, ...
            'geometry domain must contain x, y, and z bounds'));
    end
end

function axisValue = make_staggered_axis(bounds, resolution, name, errorId)
    if ~isnumeric(bounds) || ~isvector(bounds) || numel(bounds) ~= 2 || ...
            ~isreal(bounds) || any(~isfinite(bounds(:))) || ...
            bounds(1) >= bounds(2)
        throw(MException(errorId, ...
            'domain_over_l.%s must be a finite increasing pair', name));
    end
    bounds = double(bounds(:)');
    rawCount = diff(bounds) .* resolution;
    intervalCount = round(rawCount);
    if abs(rawCount - intervalCount) > 16 * eps(max(1, abs(rawCount)))
        throw(MException(errorId, ...
            'domain span times resolution must be an integer for %s', name));
    end
    offsets = (-0.5:(intervalCount + 0.5)) ./ resolution;
    axisValue = bounds(1) + offsets;
end

function tf = outer_planes_are_positive(F)
    tf = all(F([1, end], :, :) > 0, 'all') && ...
        all(F(:, [1, end], :) > 0, 'all') && ...
        all(F(:, :, [1, end]) > 0, 'all');
end
