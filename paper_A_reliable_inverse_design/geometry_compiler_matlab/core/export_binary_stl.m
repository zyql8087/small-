function summary = export_binary_stl(mesh, finalPath)
%EXPORT_BINARY_STL Write, verify, and atomically publish binary STL.

    errorId = 'MATLABGyroid:STLSerializationError';
    finalPath = validate_text_scalar(finalPath, 'final_path', errorId);
    if path_exists(finalPath)
        throw(MException('MATLABGyroid:OutputConflict', ...
            'refusing to overwrite existing STL leaf: %s', finalPath));
    end
    outputDirectory = fileparts(finalPath);
    if isempty(outputDirectory)
        outputDirectory = pwd;
    end
    if exist(outputDirectory, 'dir') ~= 7
        throw(MException(errorId, ...
            'STL output directory does not exist: %s', outputDirectory));
    end
    [vertices, faces] = validate_mesh(mesh, errorId);
    temporaryPath = [tempname(outputDirectory), '.stl'];
    temporaryCleanup = onCleanup(@() delete_if_exists(temporaryPath));
    publishedFinal = false;
    movedNestedPath = '';
    fileId = fopen(temporaryPath, 'wb', 'ieee-le');
    if fileId == -1
        throw(MException(errorId, ...
            'cannot open temporary binary STL: %s', temporaryPath));
    end
    fileCleanup = onCleanup(@() close_if_open(fileId));
    try
        header = binary_stl_header();
        fwrite(fileId, header, 'uint8');
        fwrite(fileId, uint32(size(faces, 1)), 'uint32');
        for faceIndex = 1:size(faces, 1)
            [normal, triangle] = binary_stl_facet( ...
                vertices, faces(faceIndex, :), errorId);
            fwrite(fileId, normal, 'single');
            fwrite(fileId, triangle', 'single');
            fwrite(fileId, uint16(0), 'uint16');
        end
        if fclose(fileId) ~= 0
            throw(MException(errorId, ...
                'cannot close temporary binary STL'));
        end
        expectedMesh = struct('vertices', vertices, 'faces', faces);
        verify_binary_stl(temporaryPath, expectedMesh);
        if path_exists(finalPath)
            throw(MException('MATLABGyroid:OutputConflict', ...
                'STL target appeared before publication: %s', finalPath));
        end
        [moved, message] = movefile(temporaryPath, finalPath);
        if ~moved
            throw(MException(errorId, ...
                'cannot publish binary STL: %s', message));
        end
        [~, temporaryName, temporaryExtension] = ...
            fileparts(temporaryPath);
        if exist(finalPath, 'file') == 2 && ~isfolder(finalPath)
            publishedFinal = true;
        elseif isfolder(finalPath)
            movedNestedPath = fullfile(finalPath, ...
                [temporaryName, temporaryExtension]);
            throw(MException('MATLABGyroid:OutputConflict', ...
                'STL target became a directory during publication'));
        else
            throw(MException(errorId, ...
                'STL publication did not create the exact final file'));
        end
        summary = verify_binary_stl(finalPath, expectedMesh);
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
            'binary STL serialization failed: %s', cause.message);
        wrapped = addCause(wrapped, cause);
        throw(wrapped);
    end
    clear fileCleanup temporaryCleanup;
end

function tf = path_exists(path)
    tf = exist(path, 'file') ~= 0 || exist(path, 'dir') ~= 0;
end

function [vertices, faces] = validate_mesh(mesh, errorId)
    if ~isstruct(mesh) || ~isscalar(mesh) || ...
            ~isfield(mesh, 'vertices') || ~isfield(mesh, 'faces')
        throw(MException(errorId, ...
            'mesh must contain vertices and faces'));
    end
    vertices = mesh.vertices;
    faces = mesh.faces;
    if ~isnumeric(vertices) || ~isreal(vertices) || ...
            size(vertices, 2) ~= 3 || isempty(vertices) || ...
            any(~isfinite(vertices(:))) || ~isnumeric(faces) || ...
            ~isreal(faces) || size(faces, 2) ~= 3 || isempty(faces) || ...
            any(~isfinite(faces(:))) || any(faces(:) ~= round(faces(:))) || ...
            any(faces(:) < 1) || any(faces(:) > size(vertices, 1))
        throw(MException(errorId, ...
            'mesh vertices and faces are invalid for STL serialization'));
    end
    vertices = double(vertices);
    faces = double(faces);
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
