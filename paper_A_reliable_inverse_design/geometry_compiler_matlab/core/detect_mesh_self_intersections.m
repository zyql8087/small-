function pairs = detect_mesh_self_intersections(mesh, tolerance)
%DETECT_MESH_SELF_INTERSECTIONS Find non-adjacent intersecting face pairs.

    if ~isstruct(mesh) || ~isscalar(mesh) || ...
            ~isfield(mesh, 'vertices') || ~isfield(mesh, 'faces') || ...
            ~isnumeric(mesh.vertices) || ~isnumeric(mesh.faces) || ...
            size(mesh.vertices, 2) ~= 3 || size(mesh.faces, 2) ~= 3 || ...
            any(~isfinite(mesh.vertices(:))) || ...
            any(~isfinite(mesh.faces(:)))
        throw(MException('MATLABGyroid:InvalidMesh', ...
            'self-intersection check requires a finite triangle mesh'));
    end
    if ~isnumeric(tolerance) || ~isscalar(tolerance) || ...
            ~isreal(tolerance) || ~isfinite(tolerance) || tolerance < 0
        throw(MException('MATLABGyroid:InvalidMesh', ...
            'self-intersection tolerance must be finite and nonnegative'));
    end
    vertices = double(mesh.vertices);
    faces = double(mesh.faces);
    triangles = reshape(vertices(faces', :)', 3, 3, []);
    triangles = permute(triangles, [2, 1, 3]);
    minima = squeeze(min(triangles, [], 1))';
    maxima = squeeze(max(triangles, [], 1))';
    [sortedMinX, order] = sort(minima(:, 1), 'ascend');
    pairs = zeros(0, 2);
    for orderedIndex = 1:numel(order)
        firstFace = order(orderedIndex);
        lastPosition = upper_bound( ...
            sortedMinX, maxima(firstFace, 1) + tolerance);
        if lastPosition <= orderedIndex
            continue;
        end
        candidateFaces = order((orderedIndex + 1):lastPosition);
        overlap = minima(candidateFaces, 2) <= ...
            maxima(firstFace, 2) + tolerance & ...
            maxima(candidateFaces, 2) >= ...
            minima(firstFace, 2) - tolerance & ...
            minima(candidateFaces, 3) <= ...
            maxima(firstFace, 3) + tolerance & ...
            maxima(candidateFaces, 3) >= ...
            minima(firstFace, 3) - tolerance;
        candidateFaces = candidateFaces(overlap);
        if isempty(candidateFaces)
            continue;
        end
        sharedVertex = any(ismember( ...
            faces(candidateFaces, :), faces(firstFace, :)), 2);
        candidateFaces = candidateFaces(~sharedVertex);
        for candidateIndex = 1:numel(candidateFaces)
            secondFace = candidateFaces(candidateIndex);
            if triangles_intersect_3d( ...
                    vertices(faces(firstFace, :), :), ...
                    vertices(faces(secondFace, :), :), tolerance)
                pairs(end + 1, :) = sort([firstFace, secondFace]); %#ok<AGROW>
            end
        end
    end
    if ~isempty(pairs)
        pairs = unique(sortrows(pairs), 'rows', 'stable');
    end
end

function index = upper_bound(sortedValues, target)
    low = 1;
    high = numel(sortedValues);
    index = 0;
    while low <= high
        middle = floor((low + high) / 2);
        if sortedValues(middle) <= target
            index = middle;
            low = middle + 1;
        else
            high = middle - 1;
        end
    end
end
