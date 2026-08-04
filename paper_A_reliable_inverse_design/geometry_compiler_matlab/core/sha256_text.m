function digestHex = sha256_text(value)
%SHA256_TEXT Return lowercase SHA-256 of canonical UTF-8 text.

    value = validate_text_scalar(value, 'value', ...
        'MATLABGyroid:InvalidRequest');
    try
        messageDigest = javaMethod('getInstance', ...
            'java.security.MessageDigest', 'SHA-256');
        bytes = uint8(unicode2native(value, 'UTF-8'));
        messageDigest.update(typecast(bytes(:), 'int8'));
        digestBytes = typecast(messageDigest.digest(), 'uint8');
        digestHex = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
    catch cause
        wrapped = MException('MATLABGyroid:InvalidRequest', ...
            'cannot hash canonical UTF-8 text: %s', cause.message);
        wrapped = addCause(wrapped, cause);
        throw(wrapped);
    end
end
