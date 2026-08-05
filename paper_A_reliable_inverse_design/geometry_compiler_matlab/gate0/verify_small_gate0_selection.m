function selection = verify_small_gate0_selection(selection)
%VERIFY_SMALL_GATE0_SELECTION Recompute and authenticate the 6+30 manifest.

    errorId = 'MATLABGyroid:M04Gate0NotFrozen';
    required = {'schema_version','selection_protocol','workbook_sha256', ...
        'compiler_version', ...
        'parameter_domain_manifest_sha256','descriptor_definition_sha256', ...
        'rows','selection_canonical_text','selection_sha256'};
    if ~isstruct(selection) || ~isscalar(selection) || ...
            ~all(isfield(selection, required)) || ...
            ~isequal(sort(fieldnames(selection)), sort(required(:))) || ...
            numel(selection.rows) ~= 36
        throw(MException(errorId, 'Small Gate-0 selection envelope is invalid'));
    end
    baseDirectory = fileparts(fileparts(mfilename('fullpath')));
    config = load_compiler_config(fullfile(baseDirectory, 'configs', ...
        'compiler_config.example.json'));
    contract = legacy_calibration_contract();
    require_equal(selection.schema_version, '1.0', errorId);
    require_equal(selection.selection_protocol, 'M04-v2-selection', errorId);
    require_equal(selection.workbook_sha256, contract.workbook_sha256, errorId);
    require_equal(selection.compiler_version, compiler_version(), errorId);
    require_equal(selection.parameter_domain_manifest_sha256, ...
        config.parameter_domain_manifest_sha256, errorId);
    require_equal(selection.descriptor_definition_sha256, ...
        config.descriptor_definition_sha256, errorId);
    rows = selection.rows;
    rowFields = {'sheet','method','excel_row','row_id','raw_parameters', ...
        'effective_parameters','archived_descriptors','selection_digest','role'};
    if ~isstruct(rows) || ~all(isfield(rows, rowFields)) || ...
            ~isequal(sort(fieldnames(rows)), sort(rowFields(:))) || ...
            sum(strcmp({rows.role}, 'discovery')) ~= 6 || ...
            sum(strcmp({rows.role}, 'confirmation')) ~= 30 || ...
            numel(unique(string({rows.row_id}))) ~= 36
        throw(MException(errorId, 'Small Gate-0 role or row identities are invalid'));
    end
    for index = 1:numel(rows)
        validate_row(rows(index), config, errorId);
        expectedDigest = sha256_text(sprintf('%s|%s|%d|M04-v2-selection', ...
            selection.workbook_sha256, rows(index).sheet, rows(index).excel_row));
        require_equal(rows(index).selection_digest, expectedDigest, errorId);
    end
    canonical = canonical_small_gate0_selection( ...
        selection.workbook_sha256, rows, config);
    require_equal(selection.selection_canonical_text, canonical, errorId);
    require_equal(selection.selection_sha256, sha256_text(canonical), errorId);
    require_equal(selection.selection_sha256, contract.selection_sha256, errorId);
end

function validate_row(row, config, errorId)
    sheet = validate_text_scalar(row.sheet, 'sheet', errorId);
    method = validate_text_scalar(row.method, 'method', errorId);
    rowId = validate_text_scalar(row.row_id, 'row_id', errorId);
    validate_text_scalar(row.role, 'role', errorId);
    if ~isnumeric(row.excel_row) || ~isscalar(row.excel_row) || ...
            ~isfinite(row.excel_row) || row.excel_row < 2 || ...
            row.excel_row ~= fix(row.excel_row) || ...
            ~strcmp(rowId, sprintf('%s:%d', sheet, row.excel_row))
        throw(MException(errorId, 'Small Gate-0 row identity is invalid'));
    end
    try
        expectedEffective = project_method_constraints( ...
            method, row.raw_parameters, config);
    catch cause
        wrapped = MException(errorId, ...
            'Small Gate-0 effective parameters cannot be re-derived: %s', ...
            cause.message);
        wrapped = addCause(wrapped, cause);
        throw(wrapped);
    end
    if ~same_struct(row.effective_parameters, expectedEffective)
        throw(MException(errorId, ...
            'Small Gate-0 effective parameters were overridden'));
    end
    descriptorNames = {'relativeVolume','relativeArea','thickness', ...
        'poreDiameter','areaMean'};
    archived = row.archived_descriptors;
    if ~isstruct(archived) || ~isscalar(archived) || ...
            ~all(isfield(archived, descriptorNames)) || ...
            ~isequal(sort(fieldnames(archived)), sort(descriptorNames(:)))
        throw(MException(errorId, ...
            'Small Gate-0 archived descriptors are incomplete'));
    end
    for index = 1:numel(descriptorNames)
        value = archived.(descriptorNames{index});
        if ~isnumeric(value) || ~isscalar(value) || ...
                ~isreal(value) || ~isfinite(value)
            throw(MException(errorId, ...
                'Small Gate-0 archived descriptors are invalid'));
        end
    end
end

function tf = same_struct(actual, expected)
    tf = isstruct(actual) && isscalar(actual) && ...
        isequal(sort(fieldnames(actual)), sort(fieldnames(expected)));
    if ~tf
        return;
    end
    names = fieldnames(expected);
    for index = 1:numel(names)
        if ~isequaln(actual.(names{index}), expected.(names{index}))
            tf = false;
            return;
        end
    end
end

function require_equal(actual, expected, errorId)
    actual = validate_text_scalar(actual, 'selection value', errorId);
    expected = validate_text_scalar(expected, 'expected selection value', errorId);
    if ~strcmp(actual, expected)
        throw(MException(errorId, 'Small Gate-0 selection authentication failed'));
    end
end
