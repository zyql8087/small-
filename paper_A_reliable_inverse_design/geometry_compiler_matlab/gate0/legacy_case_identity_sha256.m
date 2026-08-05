function digest = legacy_case_identity_sha256(rows)
%LEGACY_CASE_IDENTITY_SHA256 Hash an ordered Gate-0 case-identity list.

    errorId = 'MATLABGyroid:M04Gate0NotFrozen';
    required = {'row_id','method','selection_digest','excel_row'};
    if ~isstruct(rows) || isempty(rows) || ~all(isfield(rows, required))
        throw(MException(errorId, 'Gate-0 case identity list is incomplete'));
    end
    lines = cell(numel(rows), 1);
    for index = 1:numel(rows)
        rowId = validate_text_scalar(rows(index).row_id, 'row_id', errorId);
        method = validate_text_scalar(rows(index).method, 'method', errorId);
        selectionDigest = validate_text_scalar( ...
            rows(index).selection_digest, 'selection_digest', errorId);
        excelRow = rows(index).excel_row;
        if ~isnumeric(excelRow) || ~isscalar(excelRow) || ...
                ~isfinite(excelRow) || excelRow < 2 || excelRow ~= fix(excelRow)
            throw(MException(errorId, 'Gate-0 Excel row identity is invalid'));
        end
        lines{index} = sprintf('%s|%s|%s|%d', ...
            rowId, method, selectionDigest, excelRow);
    end
    digest = sha256_text([strjoin(lines, newline), newline]);
end
