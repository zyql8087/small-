function summary = verify_binary_stl(path, expectedMesh)
%VERIFY_BINARY_STL Verify binary STL structure and finite triangle payload.

    errorId = 'MATLABGyroid:STLVerificationError';
    if nargin < 2
        expectedMesh = [];
    elseif nargin ~= 2
        throw(MException(errorId, ...
            'verify_binary_stl requires one or two inputs'));
    end
    path = validate_text_scalar(path, 'stl_path', errorId);
    if exist(path, 'file') ~= 2
        throw(MException(errorId, 'binary STL not found: %s', path));
    end
    fileInfo = dir(path);
    if isempty(fileInfo) || fileInfo.bytes < 84
        throw(MException(errorId, 'binary STL is shorter than 84 bytes'));
    end
    fileId = fopen(path, 'rb', 'ieee-le');
    if fileId == -1
        throw(MException(errorId, 'cannot open binary STL: %s', path));
    end
    cleanup = onCleanup(@() fclose(fileId));
    header = fread(fileId, 80, '*uint8');
    triangleCount = fread(fileId, 1, 'uint32=>uint32');
    if numel(header) ~= 80 || isempty(triangleCount)
        throw(MException(errorId, ...
            'binary STL header or triangle count is incomplete'));
    end
    if ~isequal(header(:)', binary_stl_header())
        throw(MException(errorId, ...
            'binary STL header does not match the compiler contract'));
    end
    if isempty(expectedMesh)
        expectedVertices = [];
        expectedFaces = [];
    else
        [expectedVertices, expectedFaces] = validate_expected_mesh( ...
            expectedMesh, errorId);
        if double(triangleCount) ~= size(expectedFaces, 1)
            throw(MException(errorId, ...
                'binary STL triangle count differs from expected mesh'));
        end
    end
    expectedBytes = 84 + 50 * double(triangleCount);
    if fileInfo.bytes ~= expectedBytes
        throw(MException(errorId, ...
            'binary STL byte length does not match triangle count'));
    end
    for faceIndex = 1:double(triangleCount)
        values = fread(fileId, 12, 'single=>single');
        attribute = fread(fileId, 1, 'uint16=>uint16');
        if numel(values) ~= 12 || isempty(attribute) || ...
                any(~isfinite(values)) || attribute ~= 0
            throw(MException(errorId, ...
                'binary STL contains an incomplete or non-finite facet'));
        end
        if ~isempty(expectedMesh)
            [normal, triangle] = binary_stl_facet(expectedVertices, ...
                expectedFaces(faceIndex, :), errorId);
            expectedValues = [normal(:); reshape(triangle', [], 1)];
            if ~isequal(values, expectedValues)
                throw(MException(errorId, ...
                    'binary STL facet payload differs from expected mesh'));
            end
        end
    end
    if ~isempty(fread(fileId, 1, '*uint8'))
        throw(MException(errorId, ...
            'binary STL contains unexpected trailing bytes'));
    end
    digest = sha256_file(path, errorId, 'binary STL');
    summary = struct('byte_length', double(fileInfo.bytes), ...
        'triangle_count', double(triangleCount), ...
        'all_finite', true, 'sha256', digest);
end

function [vertices, faces] = validate_expected_mesh(mesh, errorId)
    if ~isstruct(mesh) || ~isscalar(mesh) || ...
            ~isfield(mesh, 'vertices') || ~isfield(mesh, 'faces')
        throw(MException(errorId, ...
            'expected mesh must contain vertices and faces'));
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
            'expected mesh is invalid for STL comparison'));
    end
    vertices = double(vertices);
    faces = double(faces);
end
