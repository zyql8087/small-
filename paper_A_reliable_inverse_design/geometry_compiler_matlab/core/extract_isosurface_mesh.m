function mesh = extract_isosurface_mesh(field, isoLevel)
%EXTRACT_ISOSURFACE_MESH Extract a shared-index XYZ surface mesh.

    errorId = 'MATLABGyroid:InvalidGeometry';
    required = {'x_mm', 'y_mm', 'z_mm', 'F'};
    if ~isstruct(field) || ~isscalar(field) || ...
            ~all(isfield(field, required))
        throw(MException(errorId, ...
            'field lacks x_mm, y_mm, z_mm, or F'));
    end
    if ~isnumeric(isoLevel) || ~isscalar(isoLevel) || ...
            ~isreal(isoLevel) || ~isfinite(isoLevel)
        throw(MException(errorId, ...
            'isosurface level must be a finite real scalar'));
    end
    axes = {field.x_mm, field.y_mm, field.z_mm};
    names = {'x_mm', 'y_mm', 'z_mm'};
    for axisIndex = 1:3
        validate_axis(axes{axisIndex}, names{axisIndex}, errorId);
    end
    expectedSize = [numel(field.x_mm), numel(field.y_mm), ...
        numel(field.z_mm)];
    if ~isnumeric(field.F) || ~isreal(field.F) || ...
            any(~isfinite(field.F(:))) || ...
            ~isequal(size(field.F), expectedSize)
        throw(MException(errorId, ...
            'F dimensions do not match finite XYZ axes'));
    end

    volumeYXZ = permute(double(field.F), [2, 1, 3]);
    [faces, vertices] = isosurface(double(field.x_mm(:)'), ...
        double(field.y_mm(:)'), double(field.z_mm(:)'), ...
        volumeYXZ, double(isoLevel));
    if isempty(faces) || isempty(vertices)
        throw(MException('MATLABGyroid:EmptyMesh', ...
            'zero isosurface produced an empty mesh'));
    end
    if any(~isfinite(vertices(:)))
        throw(MException(errorId, ...
            'isosurface produced non-finite vertices'));
    end

    mesh = struct();
    mesh.faces = double(faces);
    mesh.vertices = double(vertices);
    mesh.iso_level = double(isoLevel);
    mesh.global_orientation_flip = false;
end

function validate_axis(value, label, errorId)
    if ~isnumeric(value) || ~isvector(value) || numel(value) < 2 || ...
            ~isreal(value) || any(~isfinite(value(:))) || ...
            any(diff(double(value(:)')) <= 0)
        throw(MException(errorId, ...
            '%s must be a finite strictly increasing vector', label));
    end
end
