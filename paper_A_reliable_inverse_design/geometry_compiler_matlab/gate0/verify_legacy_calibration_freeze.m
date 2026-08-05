function freeze = verify_legacy_calibration_freeze(freezePath)
%VERIFY_LEGACY_CALIBRATION_FREEZE Authenticate an immutable M04 freeze.

    errorId = 'MATLABGyroid:M04Gate0NotFrozen';
    freezePath = validate_text_scalar(freezePath, 'freeze_path', errorId);
    if exist(freezePath, 'file') ~= 2 || exist(freezePath, 'dir') == 7
        throw(MException(errorId, 'calibration freeze file is missing'));
    end
    try
        freeze = jsondecode(fileread(freezePath));
    catch cause
        wrapped = MException(errorId, 'calibration freeze JSON is invalid: %s', ...
            cause.message);
        wrapped = addCause(wrapped, cause);
        throw(wrapped);
    end
    required = {'schema_version','status','selection_sha256', ...
        'workbook_sha256','compiler_version','descriptor_definition_sha256', ...
        'legacy_profile_sha256','tpms_designer_commit', ...
        'samples_per_reference_length','reference_length_mm', ...
        'reference_length_text','thresholds','density_results', ...
        'scale_statistics','discovery_results','confirmation_rows', ...
        'freeze_sha256'};
    if ~isstruct(freeze) || ~isscalar(freeze) || ...
            ~all(isfield(freeze, required)) || ...
            ~isequal(sort(fieldnames(freeze)), sort(required(:)))
        throw(MException(errorId, 'calibration freeze envelope is incomplete'));
    end
    schemaVersion = validate_text_scalar( ...
        freeze.schema_version, 'schema_version', errorId);
    status = validate_text_scalar(freeze.status, 'status', errorId);
    if ~strcmp(schemaVersion, '1.0') || ...
            ~strcmp(status, 'M04_CALIBRATION_FROZEN')
        throw(MException(errorId, 'calibration freeze fields are inconsistent'));
    end
    validate_legacy_calibration_payload(freeze);
    canonical = canonical_legacy_calibration_freeze(freeze);
    if ~strcmp(freeze.freeze_sha256, sha256_text(canonical))
        throw(MException(errorId, 'calibration freeze authentication failed'));
    end
end
