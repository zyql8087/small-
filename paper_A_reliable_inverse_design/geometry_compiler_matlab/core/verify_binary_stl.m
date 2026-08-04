function summary = verify_binary_stl(path)
%VERIFY_BINARY_STL Verify binary STL structure and finite triangle payload.

    errorId = 'MATLABGyroid:STLVerificationError';
    path = validate_text_scalar(path, 'stl_path', errorId);
    if exist(path, 'file') ~= 2
        throw(MException(errorId, 'binary STL not found: %s', path));
    end
    fileInfo = dir(path);
    if isempty(fileInfo) || fileInfo.bytes < 84
        throw(MException(errorId, 'binary STL is shorter than 84 bytes'));
    end
    fileId = fopen(path, 'rb', 'ieee-le');
    if fileId == -1
        throw(MException(errorId, 'cannot open binary STL: %s', path));
    end
    cleanup = onCleanup(@() fclose(fileId));
    header = fread(fileId, 80, '*uint8');
    triangleCount = fread(fileId, 1, 'uint32=>uint32');
    if numel(header) ~= 80 || isempty(triangleCount)
        throw(MException(errorId, ...
            'binary STL header or triangle count is incomplete'));
    end
    expectedBytes = 84 + 50 * double(triangleCount);
    if fileInfo.bytes ~= expectedBytes
        throw(MException(errorId, ...
            'binary STL byte length does not match triangle count'));
    end
    for faceIndex = 1:double(triangleCount)
        values = fread(fileId, 12, 'single=>double');
        attribute = fread(fileId, 1, 'uint16=>uint16');
        if numel(values) ~= 12 || isempty(attribute) || ...
                any(~isfinite(values))
            throw(MException(errorId, ...
                'binary STL contains an incomplete or non-finite facet'));
        end
    end
    if ~isempty(fread(fileId, 1, '*uint8'))
        throw(MException(errorId, ...
            'binary STL contains unexpected trailing bytes'));
    end
    digest = sha256_file(path, errorId, 'binary STL');
    summary = struct('byte_length', double(fileInfo.bytes), ...
        'triangle_count', double(triangleCount), ...
        'all_finite', true, 'sha256', digest);
end
