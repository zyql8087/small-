function selection = select_small_gate0_rows(sheets, workbookHash, config)
%SELECT_SMALL_GATE0_ROWS Deterministically select authenticated Small rows.

    errorId = 'MATLABGyroid:Gate0SelectionInvalid';
    expectedNames = {'class1', 'class2', 'class12'};
    expectedMethods = {'M1', 'M2', 'M3'};
    headers = {'V1a','V1b','V1c','w','relativeVolume','relativeArea', ...
        'thickness','poreDiameter','areaMean'};
    workbookHash = validate_hash(workbookHash, errorId);
    if ~isstruct(sheets) || numel(sheets) ~= 3 || ...
            ~all(isfield(sheets, {'name', 'method', 'raw'}))
        throw(MException(errorId, 'Small workbook must contain exactly three sheets'));
    end
    rows = repmat(empty_row(), 0, 1);
    for sheetIndex = 1:3
        sheet = sheets(sheetIndex);
        require_text_equal(sheet.name, expectedNames{sheetIndex}, ...
            'sheet name', errorId);
        require_text_equal(sheet.method, expectedMethods{sheetIndex}, ...
            'sheet method', errorId);
        raw = sheet.raw;
        if ~iscell(raw) || size(raw, 1) < 13 || size(raw, 2) < 9
            throw(MException(errorId, ...
                'sheet %s must contain a header and at least 12 rows', sheet.name));
        end
        assert_headers(raw(1, 1:9), headers, errorId);
        eligible = collect_rows(raw(2:end, 1:9), sheet.name, sheet.method, ...
            workbookHash, config, errorId);
        if numel(eligible) < 12
            throw(MException(errorId, ...
                'sheet %s has fewer than 12 eligible rows', sheet.name));
        end
        [~, order] = sort({eligible.selection_digest});
        eligible = eligible(order);
        for rowIndex = 1:12
            if rowIndex <= 2
                eligible(rowIndex).role = 'discovery';
            else
                eligible(rowIndex).role = 'confirmation';
            end
        end
        rows = [rows; eligible(1:12)]; %#ok<AGROW>
    end
    canonical = canonical_selection_text(workbookHash, rows, config);
    selection = struct('schema_version', '1.0', ...
        'selection_protocol', 'M04-v2-selection', ...
        'workbook_sha256', workbookHash, ...
        'compiler_version', compiler_version(), ...
        'parameter_domain_manifest_sha256', ...
        config.parameter_domain_manifest_sha256, ...
        'descriptor_definition_sha256', config.descriptor_definition_sha256, ...
        'rows', rows, 'selection_canonical_text', canonical, ...
        'selection_sha256', sha256_text(canonical));
end

function rows = collect_rows(raw, sheetName, method, workbookHash, config, errorId)
    rows = repmat(empty_row(), 0, 1);
    descriptorNames = {'relativeVolume','relativeArea','thickness', ...
        'poreDiameter','areaMean'};
    for localIndex = 1:size(raw, 1)
        values = zeros(1, 9);
        for column = 1:9
            value = raw{localIndex, column};
            if ~isnumeric(value) || ~isscalar(value) || ~isreal(value) || ...
                    ~isfinite(value)
                throw(MException(errorId, ...
                    'sheet %s row %d column %d must be finite numeric', ...
                    sheetName, localIndex + 1, column));
            end
            values(column) = double(value);
        end
        rawParameters = struct('c0', values(1), 'c1', values(2), ...
            'c2', values(3), 'w', values(4));
        try
            projected = project_method_constraints(method, rawParameters, config);
        catch cause
            wrapped = MException(errorId, ...
                'sheet %s row %d violates active method constraints: %s', ...
                sheetName, localIndex + 1, cause.message);
            wrapped = addCause(wrapped, cause);
            throw(wrapped);
        end
        archived = struct();
        for descriptorIndex = 1:numel(descriptorNames)
            archived.(descriptorNames{descriptorIndex}) = values(descriptorIndex + 4);
        end
        excelRow = localIndex + 1;
        row = empty_row();
        row.sheet = char(sheetName);
        row.method = char(method);
        row.excel_row = excelRow;
        row.row_id = sprintf('%s:%d', sheetName, excelRow);
        row.raw_parameters = rawParameters;
        row.effective_parameters = projected;
        row.archived_descriptors = archived;
        row.selection_digest = sha256_text(sprintf('%s|%s|%d|M04-v2-selection', ...
            workbookHash, sheetName, excelRow));
        row.role = '';
        rows(end + 1, 1) = row; %#ok<AGROW>
    end
end

function row = empty_row()
    row = struct('sheet', '', 'method', '', 'excel_row', 0, ...
        'row_id', '', 'raw_parameters', struct(), ...
        'effective_parameters', struct(), 'archived_descriptors', struct(), ...
        'selection_digest', '', 'role', '');
end

function assert_headers(actual, expected, errorId)
    for index = 1:numel(expected)
        actualText = validate_text_scalar(actual{index}, 'header', errorId);
        if ~strcmp(actualText, expected{index})
            throw(MException(errorId, 'Small workbook header order is invalid'));
        end
    end
end

function require_text_equal(actual, expected, label, errorId)
    actual = validate_text_scalar(actual, label, errorId);
    if ~strcmp(actual, expected)
        throw(MException(errorId, '%s does not match the frozen protocol', label));
    end
end

function value = validate_hash(value, errorId)
    value = validate_text_scalar(value, 'workbook_sha256', errorId);
    if isempty(regexp(value, '^[0-9a-f]{64}$', 'once'))
        throw(MException(errorId, 'workbook_sha256 must be lowercase SHA-256'));
    end
end

function text = canonical_selection_text(workbookHash, rows, config)
    lines = {['workbook_sha256=', workbookHash], ...
        'selection_protocol=M04-v2-selection', ...
        ['compiler_version=', compiler_version()], ...
        ['parameter_domain_manifest_sha256=', ...
        config.parameter_domain_manifest_sha256], ...
        ['descriptor_definition_sha256=', ...
        config.descriptor_definition_sha256]};
    for index = 1:numel(rows)
        row = rows(index);
        parameters = row.raw_parameters;
        archived = row.archived_descriptors;
        lines{end + 1} = sprintf([ ...
            '%s|%s|%d|%s|%s|' ...
            'c0=%.17g|c1=%.17g|c2=%.17g|w=%.17g|' ...
            'relativeVolume=%.17g|relativeArea=%.17g|' ...
            'thickness=%.17g|poreDiameter=%.17g|areaMean=%.17g'], ...
            row.sheet, row.method, row.excel_row, row.role, ...
            row.selection_digest, parameters.c0, parameters.c1, ...
            parameters.c2, parameters.w, archived.relativeVolume, ...
            archived.relativeArea, archived.thickness, ...
            archived.poreDiameter, archived.areaMean); %#ok<AGROW>
    end
    text = [strjoin(lines, newline), newline];
end
