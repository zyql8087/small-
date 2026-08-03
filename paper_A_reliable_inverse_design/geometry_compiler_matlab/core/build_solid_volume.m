function volume = build_solid_volume(field, config)
%BUILD_SOLID_VOLUME Convert an implicit field to a finite sheet-band volume.
    INVALID_GEOMETRY = 'MATLABGyroid:InvalidGeometry';
    EMPTY_SOLID = 'MATLABGyroid:EmptySolid';
    FULL_SOLID = 'MATLABGyroid:FullSolid';

    if nargin ~= 2
        throw(MException(INVALID_GEOMETRY, ...
            'build_solid_volume requires field and config'));
    end
    convention = get_convention(config, INVALID_GEOMETRY);
    if ~strcmp(convention, 'sheet_band')
        throw(MException(INVALID_GEOMETRY, ...
            'solid_convention must be "sheet_band", got "%s"', convention));
    end
    if ~isstruct(field) || ~isscalar(field) || ...
            ~isfield(field, 'G') || ~isfield(field, 'threshold')
        throw(MException(INVALID_GEOMETRY, ...
            'field must be a scalar struct containing G and threshold'));
    end
    if ~isnumeric(field.G) || isempty(field.G) || ~isreal(field.G) || ...
            any(~isfinite(field.G(:)))
        throw(MException(INVALID_GEOMETRY, ...
            'field.G must be a non-empty finite real numeric array'));
    end
    if ndims(field.G) ~= 3
        throw(MException(INVALID_GEOMETRY, ...
            'field.G must be a three-dimensional array'));
    end
    if ~isnumeric(field.threshold) || isempty(field.threshold) || ...
            ~isvector(field.threshold) || ~isreal(field.threshold) || ...
            any(~isfinite(field.threshold(:))) || ...
            any(field.threshold(:) < 0)
        throw(MException(INVALID_GEOMETRY, ...
            'field.threshold must contain finite nonnegative values'));
    end
    if numel(field.threshold) ~= size(field.G, 3)
        throw(MException(INVALID_GEOMETRY, ...
            'field.threshold length must equal size(field.G, 3)'));
    end

    threshold3d = reshape(double(field.threshold), 1, 1, []);
    solid = abs(field.G) <= threshold3d;
    solidCount = nnz(solid);
    voxelCount = numel(solid);
    if solidCount == 0
        throw(MException(EMPTY_SOLID, ...
            'sheet-band volume contains no solid voxels'));
    end
    if solidCount == voxelCount
        throw(MException(FULL_SOLID, ...
            'sheet-band volume contains no void voxels'));
    end

    volume = struct();
    volume.solid = solid;
    volume.solid_count = solidCount;
    volume.void_count = voxelCount - solidCount;
    volume.voxel_count = voxelCount;
    volume.solid_fraction = solidCount / voxelCount;
    volume.convention = convention;
end

function convention = get_convention(config, errorId)
    if ~isstruct(config) || ~isscalar(config) || ...
            ~isfield(config, 'solid_convention')
        throw(MException(errorId, ...
            'config must be a scalar struct containing solid_convention'));
    end
    convention = validate_text_scalar( ...
        config.solid_convention, 'solid_convention', errorId);
end
