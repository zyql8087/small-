function summary = export_binary_stl(mesh, finalPath)
%EXPORT_BINARY_STL Write, verify, and atomically publish binary STL.

    errorId = 'MATLABGyroid:STLSerializationError';
    finalPath = validate_text_scalar(finalPath, 'final_path', errorId);
    if exist(finalPath, 'file') == 2
        throw(MException('MATLABGyroid:OutputConflict', ...
            'refusing to overwrite existing STL: %s', finalPath));
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
    fileId = fopen(temporaryPath, 'wb', 'ieee-le');
    if fileId == -1
        throw(MException(errorId, ...
            'cannot open temporary binary STL: %s', temporaryPath));
    end
    fileCleanup = onCleanup(@() close_if_open(fileId));
    try
        header = zeros(1, 80, 'uint8');
        label = uint8('MATLABGyroid continuous CSG STL');
        header(1:numel(label)) = label;
        fwrite(fileId, header, 'uint8');
        fwrite(fileId, uint32(size(faces, 1)), 'uint32');
        for faceIndex = 1:size(faces, 1)
            triangle = single(vertices(faces(faceIndex, :), :));
            normal = cross(double(triangle(2, :) - triangle(1, :)), ...
                double(triangle(3, :) - triangle(1, :)));
            normalNorm = norm(normal);
            if ~isfinite(normalNorm) || normalNorm == 0
                throw(MException(errorId, ...
                    'cannot serialize a degenerate STL triangle'));
            end
            normal = single(normal ./ normalNorm);
            fwrite(fileId, normal, 'single');
            fwrite(fileId, triangle', 'single');
            fwrite(fileId, uint16(0), 'uint16');
        end
        if fclose(fileId) ~= 0
            throw(MException(errorId, ...
                'cannot close temporary binary STL'));
        end
        verify_binary_stl(temporaryPath);
        [moved, message] = movefile(temporaryPath, finalPath);
        if ~moved
            throw(MException(errorId, ...
                'cannot publish binary STL: %s', message));
        end
        summary = verify_binary_stl(finalPath);
    catch cause
        close_if_open(fileId);
        delete_if_exists(temporaryPath);
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
