function [digestHex, bytes] = sha256_file(filePath, errorId, label)
%SHA256_FILE Returns the lowercase SHA-256 digest of the exact file bytes.
    if nargin ~= 3
        error('MATLABGyroid:ProgrammerError', ...
            'sha256_file requires filePath, errorId, and label.');
    end
    if exist(filePath, 'file') ~= 2
        throw(MException(errorId, '%s not found: %s', label, filePath));
    end
    fileId = fopen(filePath, 'rb');
    if fileId == -1
        throw(MException(errorId, 'Cannot open %s: %s', label, filePath));
    end
    cleanup = onCleanup(@() fclose(fileId));
    try
        bytes = fread(fileId, Inf, '*uint8');
        messageDigest = javaMethod('getInstance', ...
            'java.security.MessageDigest', 'SHA-256');
        messageDigest.update(typecast(bytes, 'int8'));
        digestBytes = typecast(messageDigest.digest(), 'uint8');
        digestHex = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
    catch cause
        wrapped = MException(errorId, ...
            'Cannot hash %s "%s": %s', label, filePath, cause.message);
        wrapped = addCause(wrapped, cause);
        throw(wrapped);
    end
end
