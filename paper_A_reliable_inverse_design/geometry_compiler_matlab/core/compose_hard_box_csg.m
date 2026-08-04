function F = compose_hard_box_csg(fSheet, fBox, betaBox)
%COMPOSE_HARD_BOX_CSG Hard intersection of sheet and finite-box fields.

    errorId = 'MATLABGyroid:InvalidGeometry';
    if ~isequal(size(fSheet), size(fBox)) || ~isnumeric(fSheet) || ...
            ~isnumeric(fBox) || ~isreal(fSheet) || ~isreal(fBox) || ...
            any(~isfinite(fSheet(:))) || any(~isfinite(fBox(:)))
        throw(MException(errorId, ...
            'f_sheet and f_box must be same-sized finite real arrays'));
    end
    if ~isnumeric(betaBox) || ~isscalar(betaBox) || ...
            ~isreal(betaBox) || ~isfinite(betaBox) || betaBox <= 0
        throw(MException(errorId, ...
            'beta_box must be a finite positive scalar'));
    end

    F = max(double(fSheet), double(betaBox) .* double(fBox));
end
