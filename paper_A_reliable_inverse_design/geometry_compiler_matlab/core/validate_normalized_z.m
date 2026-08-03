function zOverL = validate_normalized_z(value, errorId)
%VALIDATE_NORMALIZED_Z Validate and convert normalized z coordinates.
    if nargin ~= 2
        error('MATLABGyroid:ProgrammerError', ...
            'validate_normalized_z requires value and errorId');
    end
    if ~isnumeric(value) || isempty(value) || ~isvector(value) || ...
            ~isreal(value) || any(~isfinite(value(:)))
        throw(MException(errorId, ...
            'z_over_l must be a non-empty finite real numeric vector'));
    end
    zOverL = double(value);
    if any(zOverL(:) < 0 | zOverL(:) > 2)
        throw(MException(errorId, ...
            'z_over_l must lie within [0, 2]'));
    end
end
