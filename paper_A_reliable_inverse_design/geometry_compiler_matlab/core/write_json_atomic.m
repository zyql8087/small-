function write_json_atomic(value, finalPath)
%WRITE_JSON_ATOMIC Verify JSON then atomically publish it.

    errorId = 'MATLABGyroid:JSONWriteError';
    finalPath = validate_text_scalar(finalPath, 'json_path', errorId);
    if path_exists(finalPath)
        throw(MException('MATLABGyroid:OutputConflict', ...
            'refusing to overwrite existing JSON leaf: %s', finalPath));
    end
    outputDirectory = fileparts(finalPath);
    if isempty(outputDirectory)
        outputDirectory = pwd;
    end
    if exist(outputDirectory, 'dir') ~= 7
        throw(MException(errorId, ...
            'JSON output directory does not exist: %s', outputDirectory));
    end
    temporaryPath = [tempname(outputDirectory), '.json'];
    temporaryCleanup = onCleanup(@() delete_if_exists(temporaryPath));
    publishedFinal = false;
    movedNestedPath = '';
    fileId = fopen(temporaryPath, 'w', 'n', 'UTF-8');
    if fileId == -1
        throw(MException(errorId, ...
            'cannot open temporary JSON: %s', temporaryPath));
    end
    fileCleanup = onCleanup(@() close_if_open(fileId));
    try
        encoded = jsonencode(value, 'PrettyPrint', true);
        fprintf(fileId, '%s', encoded);
        if fclose(fileId) ~= 0
            throw(MException(errorId, 'cannot close temporary JSON'));
        end
        jsondecode(fileread(temporaryPath));
        if path_exists(finalPath)
            throw(MException('MATLABGyroid:OutputConflict', ...
                'JSON target appeared before publication: %s', finalPath));
        end
        [moved, message] = movefile(temporaryPath, finalPath);
        if ~moved
            throw(MException(errorId, ...
                'cannot publish JSON: %s', message));
        end
        [~, temporaryName, temporaryExtension] = fileparts(temporaryPath);
        if exist(finalPath, 'file') == 2 && ~isfolder(finalPath)
            publishedFinal = true;
        elseif isfolder(finalPath)
            movedNestedPath = fullfile(finalPath, ...
                [temporaryName, temporaryExtension]);
            throw(MException('MATLABGyroid:OutputConflict', ...
                'JSON target became a directory during publication'));
        else
            throw(MException(errorId, ...
                'JSON publication did not create the exact final file'));
        end
        jsondecode(fileread(finalPath));
    catch cause
        close_if_open(fileId);
        delete_if_exists(temporaryPath);
        delete_if_exists(movedNestedPath);
        if publishedFinal
            delete_if_exists(finalPath);
        end
        if startsWith(cause.identifier, 'MATLABGyroid:')
            rethrow(cause);
        end
        wrapped = MException(errorId, ...
            'JSON serialization failed: %s', cause.message);
        wrapped = addCause(wrapped, cause);
        throw(wrapped);
    end
    clear fileCleanup temporaryCleanup;
end

function tf = path_exists(path)
    tf = exist(path, 'file') ~= 0 || exist(path, 'dir') ~= 0;
end

function close_if_open(fileId)
    if any(fopen('all') == fileId)
        fclose(fileId);
    end
end

function delete_if_exists(path)
    if exist(path, 'file') == 2
        delete(path);
    end
end
