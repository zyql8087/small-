function cellSizeOverL = evaluate_cell_size_profile( ...
        zOverL, projected, config)
%EVALUATE_CELL_SIZE_PROFILE Evaluate constant or denominator-form gamma(z).
    INVALID_REQUEST = 'MATLABGyroid:InvalidRequest';
    INVALID_GEOMETRY = 'MATLABGyroid:InvalidGeometry';

    if nargin ~= 3
        throw(MException(INVALID_REQUEST, ...
            ['evaluate_cell_size_profile requires z_over_l, projected ' ...
            'parameters, and config']));
    end
    zOverL = validate_normalized_z(zOverL, INVALID_GEOMETRY);
    method = validate_method(projected, INVALID_REQUEST);
    baseCellSize = get_base_cell_size(config, INVALID_REQUEST);

    switch method
        case 'M1'
            cellSizeOverL = baseCellSize + zeros(size(zOverL));
        case {'M2', 'M3'}
            if ~isfield(projected, 'w') || ~isnumeric(projected.w) || ...
                    ~isscalar(projected.w) || ~isreal(projected.w) || ...
                    ~isfinite(projected.w) || projected.w <= 0
                throw(MException(INVALID_REQUEST, ...
                    'projected.w must be a finite positive real numeric scalar'));
            end
            cellSizeOverL = baseCellSize + zOverL ./ projected.w;
    end

    if any(~isfinite(cellSizeOverL(:))) || any(cellSizeOverL(:) <= 0)
        throw(MException(INVALID_GEOMETRY, ...
            'cell-size profile must contain finite positive values'));
    end
end

function method = validate_method(projected, errorId)
    if ~isstruct(projected) || ~isscalar(projected) || ...
            ~isfield(projected, 'method')
        throw(MException(errorId, ...
            'projected parameters must be a scalar struct with method'));
    end
    method = validate_text_scalar(projected.method, 'projected.method', errorId);
    if ~ismember(method, {'M1', 'M2', 'M3'})
        throw(MException(errorId, ...
            'projected.method must be one of {M1, M2, M3}'));
    end
end

function baseCellSize = get_base_cell_size(config, errorId)
    if ~isstruct(config) || ~isscalar(config) || ...
            ~isfield(config, 'geometry_parameters') || ...
            ~isstruct(config.geometry_parameters) || ...
            ~isscalar(config.geometry_parameters) || ...
            ~isfield(config.geometry_parameters, 'Lz0_over_l')
        throw(MException(errorId, ...
            'config must contain geometry_parameters.Lz0_over_l'));
    end
    baseCellSize = config.geometry_parameters.Lz0_over_l;
    if ~isnumeric(baseCellSize) || ~isscalar(baseCellSize) || ...
            ~isreal(baseCellSize) || ~isfinite(baseCellSize) || ...
            baseCellSize <= 0
        throw(MException(errorId, ...
            'config.geometry_parameters.Lz0_over_l must be finite and positive'));
    end
    baseCellSize = double(baseCellSize);
end
