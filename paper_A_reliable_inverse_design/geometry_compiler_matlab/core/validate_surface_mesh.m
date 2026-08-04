function [report, validatedMesh] = validate_surface_mesh( ...
        mesh, spacingMm, meshQc)
%VALIDATE_SURFACE_MESH Apply strict shared-index surface-mesh gates.

    report = initial_report(mesh);
    validatedMesh = mesh;
    if ~isnumeric(spacingMm) || ~isscalar(spacingMm) || ...
            ~isreal(spacingMm) || ~isfinite(spacingMm) || spacingMm <= 0
        report.failure_code = 'INVALID_MESH';
        return;
    end
    if ~isstruct(meshQc) || ~isscalar(meshQc) || ...
            ~isfield(meshQc, 'min_edge_length_ratio') || ...
            ~isfield(meshQc, 'self_intersect_check') || ...
            ~isnumeric(meshQc.min_edge_length_ratio) || ...
            ~isscalar(meshQc.min_edge_length_ratio) || ...
            ~isfinite(meshQc.min_edge_length_ratio) || ...
            meshQc.min_edge_length_ratio <= 0 || ...
            ~islogical(meshQc.self_intersect_check) || ...
            ~isscalar(meshQc.self_intersect_check)
        report.failure_code = 'INVALID_MESH';
        return;
    end
    if ~isstruct(mesh) || ~isscalar(mesh) || ...
            ~isfield(mesh, 'vertices') || ~isfield(mesh, 'faces')
        report.failure_code = 'INVALID_MESH';
        return;
    end
    V = mesh.vertices;
    F = mesh.faces;
    if ~isnumeric(V) || ~isreal(V) || size(V, 2) ~= 3 || ...
            isempty(V) || any(~isfinite(V(:))) || ~isnumeric(F) || ...
            ~isreal(F) || size(F, 2) ~= 3 || isempty(F) || ...
            any(~isfinite(F(:))) || any(F(:) ~= round(F(:))) || ...
            any(F(:) < 1) || any(F(:) > size(V, 1))
        report.failure_code = 'INVALID_MESH';
        return;
    end
    V = double(V);
    F = double(F);
    validatedMesh.vertices = V;
    validatedMesh.faces = F;

    repeatedIndex = F(:, 1) == F(:, 2) | ...
        F(:, 2) == F(:, 3) | F(:, 3) == F(:, 1);
    p1 = V(F(:, 1), :);
    p2 = V(F(:, 2), :);
    p3 = V(F(:, 3), :);
    e12 = p2 - p1;
    e23 = p3 - p2;
    e31 = p1 - p3;
    crossVectors = cross(e12, p3 - p1, 2);
    doubleAreas = sqrt(sum(crossVectors .^ 2, 2));
    areaTolerance = max(spacingMm ^ 2 * 1e-12, realmin('double'));
    degenerate = repeatedIndex | doubleAreas <= 2 * areaTolerance;
    report.degenerate_face_count = nnz(degenerate);
    report.surface_area_mm2 = 0.5 * sum(doubleAreas);
    edgeLengths = [sqrt(sum(e12 .^ 2, 2)); ...
        sqrt(sum(e23 .^ 2, 2)); sqrt(sum(e31 .^ 2, 2))];
    report.minimum_edge_mm = min(edgeLengths);

    canonicalFaces = sort(F, 2);
    [~, ~, faceGroup] = unique(canonicalFaces, 'rows');
    faceMultiplicity = accumarray(faceGroup, 1);
    report.duplicate_face_count = sum(max(faceMultiplicity - 1, 0));

    directedEdges = [F(:, [1, 2]); F(:, [2, 3]); F(:, [3, 1])];
    faceOwners = repmat((1:size(F, 1))', 3, 1);
    undirectedEdges = sort(directedEdges, 2);
    [uniqueEdges, ~, edgeGroup] = unique(undirectedEdges, 'rows');
    incidence = accumarray(edgeGroup, 1);
    report.edge_count = size(uniqueEdges, 1);
    report.boundary_edge_count = nnz(incidence == 1);
    report.nonmanifold_edge_count = nnz(incidence > 2);
    direction = ones(size(directedEdges, 1), 1);
    direction(directedEdges(:, 1) ~= undirectedEdges(:, 1)) = -1;
    directionSum = accumarray(edgeGroup, direction);
    report.inconsistent_edge_count = nnz( ...
        incidence == 2 & directionSum ~= 0);
    report.component_count = face_component_count( ...
        edgeGroup, incidence, faceOwners, size(F, 1));

    if any(degenerate)
        report.failure_code = 'DEGENERATE_MESH';
        return;
    end
    if report.duplicate_face_count > 0
        report.failure_code = 'DUPLICATE_FACE';
        return;
    end
    if report.minimum_edge_mm < ...
            spacingMm * double(meshQc.min_edge_length_ratio)
        report.failure_code = 'DEGENERATE_MESH';
        return;
    end
    if report.boundary_edge_count > 0
        report.failure_code = 'OPEN_MESH';
        return;
    end
    if report.nonmanifold_edge_count > 0
        report.failure_code = 'NONMANIFOLD_MESH';
        return;
    end
    if report.inconsistent_edge_count > 0
        report.failure_code = 'INCONSISTENT_ORIENTATION';
        return;
    end
    signedVolume = signed_volume(V, F);
    if signedVolume < 0
        F = F(:, [1, 3, 2]);
        validatedMesh.faces = F;
        signedVolume = signed_volume(V, F);
        report.global_orientation_flip = true;
    end
    report.signed_volume_mm3 = signedVolume;
    if meshQc.self_intersect_check
        try
            tolerance = max(spacingMm * 1e-9, 64 * eps);
            intersectionPairs = detect_mesh_self_intersections( ...
                validatedMesh, tolerance);
        catch
            report.failure_code = 'SELF_INTERSECTION_CHECK_UNAVAILABLE';
            return;
        end
        report.self_intersection_pair_count = size(intersectionPairs, 1);
        report.self_intersection_pairs = intersectionPairs( ...
            1:min(20, size(intersectionPairs, 1)), :);
        if ~isempty(intersectionPairs)
            report.failure_code = 'SELF_INTERSECTION';
            return;
        end
    else
        report.self_intersection_pair_count = 0;
        report.self_intersection_pairs = zeros(0, 2);
    end
    if report.component_count ~= 1
        report.failure_code = 'DISCONNECTED_SOLID';
        return;
    end
    report.valid = true;
    report.failure_code = '';
end

function report = initial_report(mesh)
    vertexCount = 0;
    faceCount = 0;
    if isstruct(mesh) && isscalar(mesh)
        if isfield(mesh, 'vertices') && isnumeric(mesh.vertices)
            vertexCount = size(mesh.vertices, 1);
        end
        if isfield(mesh, 'faces') && isnumeric(mesh.faces)
            faceCount = size(mesh.faces, 1);
        end
    end
    report = struct('valid', false, 'failure_code', 'INTERNAL_ERROR', ...
        'vertex_count', vertexCount, 'face_count', faceCount, ...
        'edge_count', NaN, 'boundary_edge_count', NaN, ...
        'nonmanifold_edge_count', NaN, 'inconsistent_edge_count', NaN, ...
        'component_count', NaN, 'duplicate_face_count', NaN, ...
        'degenerate_face_count', NaN, 'minimum_edge_mm', NaN, ...
        'surface_area_mm2', NaN, 'signed_volume_mm3', NaN, ...
        'global_orientation_flip', false, ...
        'self_intersection_pair_count', NaN, ...
        'self_intersection_pairs', zeros(0, 2));
end

function count = face_component_count(edgeGroup, incidence, owners, nFaces)
    twoUseGroups = find(incidence == 2);
    adjacency = zeros(numel(twoUseGroups), 2);
    for groupIndex = 1:numel(twoUseGroups)
        adjacentFaces = owners(edgeGroup == twoUseGroups(groupIndex));
        adjacency(groupIndex, :) = adjacentFaces(:)';
    end
    if isempty(adjacency)
        count = nFaces;
        return;
    end
    labels = conncomp(graph(adjacency(:, 1), adjacency(:, 2), [], nFaces));
    count = max(labels);
end

function volume = signed_volume(vertices, faces)
    p1 = vertices(faces(:, 1), :);
    p2 = vertices(faces(:, 2), :);
    p3 = vertices(faces(:, 3), :);
    volume = sum(dot(p1, cross(p2, p3, 2), 2)) / 6;
end
