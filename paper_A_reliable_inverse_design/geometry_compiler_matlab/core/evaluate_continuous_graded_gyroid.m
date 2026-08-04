function sample = evaluate_continuous_graded_gyroid( ...
        projected, config, xOverL, yOverL, zOverL)
%EVALUATE_CONTINUOUS_GRADED_GYROID Evaluate the field on arbitrary axes.

    errorId = 'MATLABGyroid:InvalidGeometry';
    xOverL = validate_axis(xOverL, 'x_over_l', errorId);
    yOverL = validate_axis(yOverL, 'y_over_l', errorId);
    zOverL = validate_axis(zOverL, 'z_over_l', errorId);
    domain = get_domain(config, errorId);
    profileZ = min(max(zOverL, domain.z(1)), domain.z(2));
    threshold = evaluate_threshold_profile(profileZ, projected);
    cellSize = evaluate_cell_size_profile(profileZ, projected, config);

    xPhase = 2 * pi * xOverL / config.geometry_parameters.Lx_over_l;
    yPhase = 2 * pi * yOverL / config.geometry_parameters.Ly_over_l;
    zPhase = 2 * pi * zOverL ./ cellSize;
    sinX = reshape(sin(xPhase), [], 1, 1);
    cosX = reshape(cos(xPhase), [], 1, 1);
    sinY = reshape(sin(yPhase), 1, [], 1);
    cosY = reshape(cos(yPhase), 1, [], 1);
    sinZ = reshape(sin(zPhase), 1, 1, []);
    cosZ = reshape(cos(zPhase), 1, 1, []);
    G = sinX .* cosY + sinY .* cosZ + sinZ .* cosX;
    if ~isreal(G) || any(~isfinite(G(:)))
        throw(MException(errorId, ...
            'continuous Gyroid field must be finite and real'));
    end

    sample = struct();
    sample.G = G;
    sample.threshold = threshold;
    sample.cell_size_over_l = cellSize;
    sample.profile_z_over_l = profileZ;
end

function axisValue = validate_axis(value, label, errorId)
    if ~isnumeric(value) || ~isvector(value) || isempty(value) || ...
            ~isreal(value) || any(~isfinite(value(:)))
        throw(MException(errorId, ...
            '%s must be a non-empty finite real numeric vector', label));
    end
    axisValue = double(value(:)');
    if numel(axisValue) > 1 && any(diff(axisValue) <= 0)
        throw(MException(errorId, ...
            '%s must be strictly increasing', label));
    end
end

function domain = get_domain(config, errorId)
    if ~isstruct(config) || ~isscalar(config) || ...
            ~isfield(config, 'geometry_parameters') || ...
            ~isstruct(config.geometry_parameters) || ...
            ~isscalar(config.geometry_parameters) || ...
            ~isfield(config.geometry_parameters, 'domain_over_l') || ...
            ~isstruct(config.geometry_parameters.domain_over_l) || ...
            ~isscalar(config.geometry_parameters.domain_over_l) || ...
            ~isfield(config.geometry_parameters.domain_over_l, 'z') || ...
            ~isfield(config.geometry_parameters, 'Lx_over_l') || ...
            ~isfield(config.geometry_parameters, 'Ly_over_l')
        throw(MException(errorId, ...
            'config does not contain the continuous geometry contract'));
    end
    domain = config.geometry_parameters.domain_over_l;
    if ~isnumeric(domain.z) || numel(domain.z) ~= 2 || ...
            any(~isfinite(domain.z(:))) || domain.z(1) >= domain.z(2)
        throw(MException(errorId, ...
            'config geometry z domain must be a finite increasing pair'));
    end
end
