function textValue = validate_text_scalar(value, label, errorId)
%VALIDATE_TEXT_SCALAR Return a character row after strict text validation.
    if ischar(value) && isrow(value)
        textValue = value;
        return;
    end
    if isstring(value) && isscalar(value)
        textValue = char(value);
        return;
    end
    throw(MException(errorId, ...
        '%s must be a character row vector or string scalar, got: %s', ...
        label, class(value)));
end
