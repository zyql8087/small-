function result = compute_physical_m04_descriptors( ...
        solid, spacingMm, mesh, boundsMm, definitionSha256)
%COMPUTE_PHYSICAL_M04_DESCRIPTORS Compute finite-specimen M04 descriptors.

    errorId = 'MATLABGyroid:DescriptorProfileInvalid';
    validate_mask(solid, errorId);
    validate_positive_scalar(spacingMm, 'spacing_mm', errorId);
    validate_bounds(boundsMm, solid, spacingMm, errorId);
    [surfaceAreaMm2, triangleCount] = mesh_surface_area(mesh, boundsMm, errorId);
    validate_hash(definitionSha256, errorId);

    voidMask = ~solid;
    solidComponents = bwconncomp(solid, 26);
    voidComponents = bwconncomp(voidMask, 26);
    componentSizes = cellfun(@numel, voidComponents.PixelIdxList);
    [selectedVoidComponentSize, selectedVoidComponentIndex] = max(componentSizes);

    distanceToVoid = bwdist(voidMask);
    skeleton = bwskel(solid);
    if ~any(skeleton(:))
        throw(MException(errorId, ...
            'physical descriptor solid skeleton must not be empty'));
    end
    thickness = 2 * median(distanceToVoid(skeleton)) * double(spacingMm);

    paddedVoid = padarray(voidMask, [1, 1, 1], false, 'both');
    paddedDistance = bwdist(~paddedVoid);
    voidDistance = paddedDistance(2:end-1, 2:end-1, 2:end-1);
    poreDiameter = 2 * max(voidDistance( ...
        voidComponents.PixelIdxList{selectedVoidComponentIndex})) * ...
        double(spacingMm);

    sliceIndices = round(linspace(1, size(solid, 3), 26));
    sliceAreas = zeros(1, 0);
    for sliceIndex = 1:numel(sliceIndices)
        components = bwconncomp(voidMask(:, :, sliceIndices(sliceIndex)), 8);
        if components.NumObjects > 0
            areas = cellfun(@numel, components.PixelIdxList) .* ...
                double(spacingMm)^2;
            sliceAreas(end + 1) = max(areas); %#ok<AGROW>
        end
    end
    if isempty(sliceAreas)
        throw(MException(errorId, ...
            'physical descriptor has no nonempty void slices'));
    end

    dimensionsMm = boundsMm(:, 2) - boundsMm(:, 1);
    values = struct('relativeVolume', nnz(solid) / numel(solid), ...
        'relativeArea', surfaceAreaMm2 / prod(dimensionsMm), ...
        'thickness', thickness, 'poreDiameter', poreDiameter, ...
        'areaMean', mean(sliceAreas));
    result = struct('profile', 'physical_m04', ...
        'definition_sha256', char(definitionSha256), ...
        'sampling', struct('grid_convention', 'm03_cell_centered_interior', ...
        'voxel_spacing_mm', double(spacingMm), ...
        'physical_bounds_mm', boundsMm), ...
        'units', struct('relativeVolume', 'dimensionless', ...
        'relativeArea', 'mm^-1', 'thickness', 'mm', ...
        'poreDiameter', 'mm', 'areaMean', 'mm2'), ...
        'values', values, ...
        'diagnostics', struct('solid_component_count', ...
        solidComponents.NumObjects, 'void_component_count', ...
        voidComponents.NumObjects, 'skeleton_voxel_count', nnz(skeleton), ...
        'selected_void_component_index', selectedVoidComponentIndex, ...
        'selected_void_component_size', selectedVoidComponentSize, ...
        'largest_void_component_size', selectedVoidComponentSize, ...
        'slice_indices', sliceIndices, ...
        'nonempty_slice_count', numel(sliceAreas), ...
        'voxel_spacing_mm', double(spacingMm), ...
        'physical_bounds_mm', boundsMm, ...
        'surface_area_mm2', surfaceAreaMm2, ...
        'surface_triangle_count', triangleCount));
    validate_descriptor_result(result, 'physical_m04', char(definitionSha256));
end

function validate_mask(solid, errorId)
    if ~islogical(solid) || ndims(solid) ~= 3 || any(size(solid) < 2, 'all')
        throw(MException(errorId, ...
            'physical descriptor solid mask must be a three-dimensional logical array'));
    end
    if ~any(solid(:)) || ~any(~solid(:))
        throw(MException(errorId, ...
            'physical descriptor solid mask must contain both solid and void'));
    end
end

function validate_positive_scalar(value, label, errorId)
    if ~isnumeric(value) || ~isscalar(value) || ~isreal(value) || ...
            ~isfinite(value) || value <= 0
        throw(MException(errorId, ...
            '%s must be a finite positive numeric scalar', label));
    end
end

function validate_bounds(boundsMm, solid, spacingMm, errorId)
    if ~isnumeric(boundsMm) || ~isequal(size(boundsMm), [3, 2]) || ...
            ~isreal(boundsMm) || any(~isfinite(boundsMm(:))) || ...
            any(boundsMm(:, 1) >= boundsMm(:, 2))
        throw(MException(errorId, ...
            'physical_bounds_mm must be a finite increasing 3-by-2 matrix'));
    end
    dimensionsMm = boundsMm(:, 2) - boundsMm(:, 1);
    expectedDimensionsMm = double(size(solid)).' .* double(spacingMm);
    tolerance = 32 * eps(max(1, max(abs([dimensionsMm; expectedDimensionsMm]))));
    if any(abs(dimensionsMm - expectedDimensionsMm) > tolerance)
        throw(MException(errorId, ...
            'physical_bounds_mm must match isotropic voxel spacing and mask size'));
    end
end

function [surfaceAreaMm2, triangleCount] = mesh_surface_area(mesh, boundsMm, errorId)
    if ~isstruct(mesh) || ~isscalar(mesh) || ...
            ~all(isfield(mesh, {'vertices', 'faces'}))
        throw(MException(errorId, 'physical descriptor mesh is incomplete'));
    end
    if ~isnumeric(mesh.vertices) || ~isreal(mesh.vertices) || ...
            ~isnumeric(mesh.faces) || ~isreal(mesh.faces)
        throw(MException(errorId, 'physical descriptor mesh is invalid'));
    end
    vertices = double(mesh.vertices);
    faces = double(mesh.faces);
    if size(vertices, 2) ~= 3 || ...
            size(faces, 2) ~= 3 || isempty(vertices) || isempty(faces) || ...
            any(~isfinite(vertices(:))) || any(~isfinite(faces(:))) || ...
            any(faces(:) < 1) || any(faces(:) > size(vertices, 1)) || ...
            any(mod(faces(:), 1) ~= 0)
        throw(MException(errorId, 'physical descriptor mesh is invalid'));
    end
    validate_closed_surface_topology(faces, errorId);
    tolerance = 64 * eps(max(1, max(abs(boundsMm(:)))));
    if any(vertices < boundsMm(:, 1)' - tolerance, 'all') || ...
            any(vertices > boundsMm(:, 2)' + tolerance, 'all')
        throw(MException(errorId, ...
            'physical descriptor mesh lies outside physical_bounds_mm'));
    end
    edgeOne = vertices(faces(:, 2), :) - vertices(faces(:, 1), :);
    edgeTwo = vertices(faces(:, 3), :) - vertices(faces(:, 1), :);
    triangleAreas = 0.5 .* vecnorm(cross(edgeOne, edgeTwo, 2), 2, 2);
    surfaceAreaMm2 = sum(triangleAreas);
    if ~isfinite(surfaceAreaMm2) || surfaceAreaMm2 <= 0
        throw(MException(errorId, ...
            'physical descriptor surface area must be finite and positive'));
    end
    triangleCount = size(faces, 1);
end

function validate_closed_surface_topology(faces, errorId)
    directedEdges = [faces(:, [1, 2]); faces(:, [2, 3]); faces(:, [3, 1])];
    [~, ~, edgeGroup] = unique(sort(directedEdges, 2), 'rows');
    incidence = accumarray(edgeGroup, 1);
    if any(incidence ~= 2)
        throw(MException(errorId, ...
            'physical descriptor mesh must be a closed two-manifold surface'));
    end
end

function validate_hash(value, errorId)
    if ~(ischar(value) && isrow(value)) && ~(isstring(value) && isscalar(value))
        throw(MException(errorId, 'definition_sha256 must be text'));
    end
    value = char(value);
    if isempty(regexp(value, '^[0-9a-f]{64}$', 'once'))
        throw(MException(errorId, ...
            'definition_sha256 must be 64 lowercase hexadecimal characters'));
    end
end
