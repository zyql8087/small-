function threshold = evaluate_threshold_profile(zOverL, projected)
%EVALUATE_THRESHOLD_PROFILE Evaluate the frozen Small threshold profile.
    INVALID_REQUEST = 'MATLABGyroid:InvalidRequest';
    INVALID_GEOMETRY = 'MATLABGyroid:InvalidGeometry';

    if nargin ~= 2
        throw(MException(INVALID_REQUEST, ...
            'evaluate_threshold_profile requires z_over_l and projected parameters'));
    end
    zOverL = validate_normalized_z(zOverL, INVALID_GEOMETRY);
    method = validate_projected_method(projected, INVALID_REQUEST);

    switch method
        case {'M1', 'M3'}
            require_finite_fields(projected, {'c0', 'c1', 'c2'}, ...
                INVALID_REQUEST);
            threshold = zeros(size(zOverL));
            lowerHalf = zOverL <= 1;
            threshold(lowerHalf) = projected.c0 + ...
                (projected.c1 - projected.c0) .* zOverL(lowerHalf);
            upperHalf = ~lowerHalf;
            threshold(upperHalf) = projected.c1 + ...
                (projected.c2 - projected.c1) .* ...
                (zOverL(upperHalf) - 1);
        case 'M2'
            require_finite_fields(projected, {'c_projected'}, ...
                INVALID_REQUEST);
            threshold = projected.c_projected + zeros(size(zOverL));
    end

    if any(~isfinite(threshold(:)))
        throw(MException(INVALID_GEOMETRY, ...
            'threshold profile contains non-finite values'));
    end
end

function method = validate_projected_method(projected, errorId)
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

function require_finite_fields(value, names, errorId)
    for fieldIndex = 1:numel(names)
        fieldName = names{fieldIndex};
        if ~isfield(value, fieldName)
            throw(MException(errorId, ...
                'projected.%s missing required field', fieldName));
        end
        fieldValue = value.(fieldName);
        if ~isnumeric(fieldValue) || ~isscalar(fieldValue) || ...
                ~isreal(fieldValue) || ~isfinite(fieldValue)
            throw(MException(errorId, ...
                'projected.%s must be a finite real numeric scalar', ...
                fieldName));
        end
    end
end
