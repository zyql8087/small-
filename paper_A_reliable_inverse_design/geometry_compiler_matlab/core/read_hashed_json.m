function [value, actualHash] = read_hashed_json( ...
        filePath, declaredHash, frozenHash, hashField, label, errorId)
%READ_HASHED_JSON Hash and parse the same immutable JSON file bytes.
    if nargin ~= 6
        error('MATLABGyroid:ProgrammerError', ...
            'read_hashed_json requires six arguments.');
    end

    [actualHash, bytes] = sha256_file(filePath, errorId, lower(label));
    if ~strcmp(actualHash, declaredHash)
        throw(MException(errorId, ...
            '%s mismatch: declared=%s actual=%s', ...
            hashField, declaredHash, actualHash));
    end
    if ~strcmp(actualHash, frozenHash)
        throw(MException(errorId, ...
            '%s does not match frozen contract value', hashField));
    end

    try
        raw = native2unicode(bytes(:)', 'UTF-8');
        value = jsondecode(raw);
    catch cause
        wrapped = MException(errorId, ...
            '%s JSON parsing failed: %s', label, cause.message);
        wrapped = addCause(wrapped, cause);
        throw(wrapped);
    end
end
