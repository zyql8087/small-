function selection = prepare_small_gate0_selection(workbookPath, outputPath)
%PREPARE_SMALL_GATE0_SELECTION Authenticate workbook and publish 6+30 rows.

    errorId = 'MATLABGyroid:Gate0SelectionInvalid';
    expectedHash = 'b4544b09c2688af8bc7aeeca5140a5d4c1cfc1c5b262709c9618c030d90fa561';
    baseDirectory = fileparts(fileparts(mfilename('fullpath')));
    addpath(fullfile(baseDirectory, 'core'));
    workbookPath = validate_text_scalar(workbookPath, 'workbook_path', errorId);
    outputPath = validate_text_scalar(outputPath, 'output_path', errorId);
    actualHash = sha256_file(workbookPath, errorId, 'Small test workbook');
    if ~strcmp(actualHash, expectedHash)
        throw(MException(errorId, ...
            'Small test workbook SHA-256 does not match the frozen source'));
    end
    names = {'class1', 'class2', 'class12'};
    methods = {'M1', 'M2', 'M3'};
    try
        available = sheetnames(workbookPath);
    catch cause
        wrapped = MException(errorId, 'cannot list Small workbook sheets: %s', ...
            cause.message);
        wrapped = addCause(wrapped, cause);
        throw(wrapped);
    end
    if ~isequal(cellstr(available(:))', names)
        throw(MException(errorId, 'Small workbook sheet order/count is invalid'));
    end
    sheets = repmat(struct('name', '', 'method', '', 'raw', []), 3, 1);
    for index = 1:3
        try
            raw = readcell(workbookPath, 'Sheet', names{index});
        catch cause
            wrapped = MException(errorId, 'cannot read sheet %s: %s', ...
                names{index}, cause.message);
            wrapped = addCause(wrapped, cause);
            throw(wrapped);
        end
        sheets(index).name = names{index};
        sheets(index).method = methods{index};
        sheets(index).raw = raw;
    end
    configPath = fullfile(baseDirectory, 'configs', ...
        'compiler_config.example.json');
    config = load_compiler_config(configPath);
    selection = select_small_gate0_rows(sheets, actualHash, config);
    write_json_atomic(selection, outputPath);
end
